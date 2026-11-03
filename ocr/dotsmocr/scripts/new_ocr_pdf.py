"""Local dots.mocr PDF client; preserve native output per page."""
import argparse
import base64
import hashlib
import http.client
import io
import json
import math
import re
import time
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import nullcontext
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
MODELS = json.loads((LAB / 'config/new_ocr_models.json').read_text(encoding='utf-8'))
SETTINGS = {'image_dpi': 200, 'max_pixels': 4014080, 'max_tokens': 24000,
            'max_model_len': 32768, 'workers': 1, 'quantization': None}
# Greedy primary layout pass; the fixed seed pins vLLM's per-request generator.
DOTS_SAMPLING = {'temperature': 0.0, 'top_p': 1.0, 'seed': 1}
NATIVE_SIDECAR = 'dotsmocr-layout/2'
# Opt-in (--rotation-retry): a dots.mocr page that hits the token limit is retried at most
# twice, turned clockwise then counter-clockwise; landscape forms printed sideways loop on rows.
ROTATIONS = {'cw90': -90, 'ccw90': 90}
# Opt-in (--loop-retry): a page that hit the token limit or the client timeout (a loop that did not
# reach the limit in time) and was not rescued by a turn is read upright again with each setting in
# turn; greedy decoding repeats empty form rows or the last regions until the limit.
LOOP_SETTINGS = ({'repetition_penalty': 1.1}, {'frequency_penalty': 0.3})
CLIENT_TIMEOUT = 900
LAYOUT_TIMEOUT = 180
# Text-bearing regions are wider than tall when upright; Page-header/footer are often one digit.
UPRIGHT_TEXT = {'Text', 'Title', 'Section-header', 'List-item', 'Footnote', 'Caption'}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def model_manifest(engine):
    return MODELS[engine]


def read_picture_stream(response):
    chunks, parts = [], []
    finish, local_stop, usage = None, None, None
    for line in response:
        if not line.startswith(b'data: '):
            continue
        if line.strip() == b'data: [DONE]':
            break
        chunk = json.loads(line[6:])
        chunks.append(chunk)
        if chunk.get('error'):
            raise ValueError(f'Picture OCR stream error: {chunk["error"]}')
        usage = chunk.get('usage') or usage
        for choice in chunk.get('choices', []):
            parts.append(choice['delta'].get('content') or '')
            finish = choice.get('finish_reason') or finish
        text = ''.join(parts)
        if len(text) >= 128 and any(text[-size:].strip() and text.endswith(text[-size:] * 8)
                                    for size in range(1, min(64, len(text) // 8) + 1)):
            local_stop = 'tail_repetition'
            break
    return {'id': chunks[0].get('id') if chunks else None, 'model': 'dotsmocr',
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': ''.join(parts)},
                         'finish_reason': finish}], 'usage': usage,
            'local_stop_reason': local_stop, 'stream_chunks': chunks}


def read_layout_stream(response, deadline=None):
    """Keep partial layout evidence; abort long repeated tails before they fill the KV cache."""
    chunks, parts = [], []
    finish, local_stop, usage, error = None, None, None, None
    length, next_check = 0, 12000
    deadline = deadline if deadline is not None else time.monotonic() + LAYOUT_TIMEOUT
    # urllib has no public read-timeout setter; shrink the socket timeout after headers and every SSE event.
    connection = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
    lines = iter(response)
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('layout page deadline exceeded')
            if connection is not None:
                connection.settimeout(remaining)
            line = next(lines, b'')
            if not line:
                break
            if not line.startswith(b'data: '):
                continue
            if line.strip() == b'data: [DONE]':
                break
            chunk = json.loads(line[6:])
            chunks.append(chunk)
            if chunk.get('error'):
                raise ValueError(f'Layout OCR stream error: {chunk["error"]}')
            usage = chunk.get('usage') or usage
            for choice in chunk.get('choices', []):
                part = choice['delta'].get('content') or ''
                parts.append(part)
                length += len(part)
                finish = choice.get('finish_reason') or finish
            if finish is None and length >= next_check:
                tail = ''.join(parts)[-8192:]
                if any(tail[-size:].strip() and tail.endswith(tail[-size:] * 24)
                       for size in range(1, min(256, len(tail) // 24) + 1)):
                    local_stop = 'tail_repetition'
                    break
                next_check = length + 1024
            if time.monotonic() >= deadline:
                raise TimeoutError('layout page deadline exceeded')
    except (OSError, http.client.IncompleteRead) as exc:
        error = f'{type(exc).__name__}: {exc}'
    native = {'id': chunks[0].get('id') if chunks else None, 'model': 'dotsmocr',
              'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': ''.join(parts)},
                           'finish_reason': finish}], 'usage': usage,
              'local_stop_reason': local_stop, 'stream_chunks': chunks}
    if error:
        native.update(client_error=error, client_timeout_seconds=LAYOUT_TIMEOUT)
    return native


def request_image(engine, image, max_tokens, prompt=None, temperature=0.0, picture_ocr=False,
                  top_p=1.0, seed=None, layout_stream=False, penalties=None):
    if engine != 'dotsmocr':
        raise ValueError('Only dots.mocr is supported')
    if prompt is None:
        prompt = (LAB / 'config/dotsmocr_prompt.txt').read_text(encoding='utf-8').strip()
    prompt = '<|img|><|imgpad|><|endofimg|>' + prompt
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    payload = {'model': engine, 'messages': [{'role': 'user', 'content': [
        {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')}},
        {'type': 'text', 'text': prompt}]}], 'max_tokens': max_tokens,
        'temperature': temperature, 'top_p': top_p}
    if seed is not None:
        payload['seed'] = seed
    if penalties:
        payload.update(penalties)
    if picture_ocr or layout_stream:
        payload.update(stream=True, stream_options={'include_usage': True})
    request = urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',
        data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    deadline = time.monotonic() + LAYOUT_TIMEOUT
    with urllib.request.urlopen(request, timeout=LAYOUT_TIMEOUT if layout_stream else CLIENT_TIMEOUT) as response:
        if picture_ocr:
            return read_picture_stream(response)
        if layout_stream:
            return read_layout_stream(response, deadline)
        return json.load(response)


def create_runtime(engine, loop_retry=False):
    import torch

    if engine != 'dotsmocr':
        raise ValueError('Only dots.mocr is supported')
    if not torch.cuda.is_available():
        raise RuntimeError('dotsmocr requires CUDA; CPU fallback is disabled')
    with urllib.request.urlopen('http://127.0.0.1:8080/v1/models', timeout=10) as response:
        served = json.load(response)['data']
    if not any(model['id'] == 'dotsmocr' and model['root'] == '/data/model'
               and model['max_model_len'] == SETTINGS['max_model_len'] for model in served):
        raise RuntimeError('The pinned local dotsmocr checkpoint/profile is not served')
    info = {'gpu': torch.cuda.get_device_name(0), 'cuda': torch.version.cuda,
            'backend': 'vllm', 'packages': {name: version(name) for name in
                                            ('torch', 'pillow', 'pymupdf', 'vllm', 'transformers')}}
    def recognize(image, max_tokens=SETTINGS['max_tokens'], penalties=None):
        return request_image(engine, image, max_tokens, penalties=penalties,
                             layout_stream=loop_retry, **DOTS_SAMPLING)
    recognize.timeout_seconds = LAYOUT_TIMEOUT if loop_retry else CLIENT_TIMEOUT
    return recognize, info


def recognize_picture_text(native, image):
    settings = json.loads((LAB / 'config/dotsmocr_picture_ocr.json').read_text(encoding='utf-8'))
    if not settings['enabled']:
        return
    cells = decode_native('dotsmocr', native)['layout']
    targets = [(index, cell) for index, cell in enumerate(cells)
               if cell['category'] == 'Picture' and not cell.get('text')]
    if not targets:
        return
    native['picture_ocr_config'] = settings
    native['picture_ocr'] = []
    width, height = image.size
    padding = settings['padding_pixels']
    recovery = settings.get('recover_repetitions', False)
    for index, cell in targets:
        left, top, right, bottom = cell['bbox']
        attempts = []
        record = {'layout_index': index, 'bbox': cell['bbox']}
        for margin in ([padding, 128] if recovery and padding < 128 else [padding]):
            box = [max(0, int(left) - margin), max(0, int(top) - margin),
                   min(width, int(right) + margin), min(height, int(bottom) + margin)]
            if box[0] >= box[2] or box[1] >= box[3]:
                raise ValueError(f'Invalid Picture region: {cell["bbox"]}')
            crop = image.crop(box)
            started = time.perf_counter()
            response = request_image('dotsmocr', crop, settings['max_tokens'],
                                     prompt=settings['prompt'], temperature=settings['temperature'],
                                     picture_ocr=recovery)
            attempts.append({'crop_bbox': box, 'image_size': list(crop.size),
                             'elapsed_seconds': round(time.perf_counter() - started, 6), 'native': response})
            record.update(attempts[-1])
            if recovery:
                record['attempts'] = attempts
            if len(attempts) == 1:
                native['picture_ocr'].append(record)
            if response['choices'][0]['finish_reason'] == 'stop' and not response.get('local_stop_reason'):
                break


def sideways_text(cells):
    """True unless there is text and every text-bearing region is shorter than three widths."""
    text = [cell['bbox'] for cell in cells if cell['category'] in UPRIGHT_TEXT]
    return not text or any(b[3] - b[1] >= 3 * (b[2] - b[0]) for b in text)


def unrotate_bbox(bbox, rotation, size):
    """Map a bbox from the turned image back to the original (width, height) page image."""
    left, top, right, bottom = bbox
    width, height = size
    if rotation == 'cw90':
        return [top, height - right, bottom, height - left]
    return [width - bottom, left, width - top, right]


def timed_out(error, timeout_seconds=CLIENT_TIMEOUT):
    """Native record of a request the client abandoned; it has no model output to decode."""
    return {'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': None}, 'finish_reason': None}],
            'client_error': f'{type(error).__name__}: {error}', 'client_timeout_seconds': timeout_seconds}


def recognize_guarded(recognize, image, **settings):
    try:
        return recognize(image, **settings)
    except TimeoutError as error:
        return timed_out(error, getattr(recognize, 'timeout_seconds', CLIENT_TIMEOUT))


def retry_trigger(native):
    """Why the primary is unfinished, otherwise None."""
    if native.get('client_error'):
        return 'timeout'
    if native.get('local_stop_reason') == 'tail_repetition':
        return 'tail_repetition'
    return 'length' if native['choices'][0]['finish_reason'] == 'length' else None


def loop_cells(native):
    """Layout of a finished upright retry without repeated regions, otherwise None."""
    choice = native['choices'][0]
    if choice['finish_reason'] != 'stop' or native.get('local_stop_reason') or native.get('client_error'):
        return None
    try:
        cells = json.loads(choice['message']['content'] or '')
    except json.JSONDecodeError:
        return None
    if not isinstance(cells, list) or not cells or any(
            not isinstance(cell, dict) or 'bbox' not in cell or 'category' not in cell for cell in cells):
        return None
    if any(b[3] - b[1] >= 3 * (b[2] - b[0]) for b in (c['bbox'] for c in cells if c['category'] in UPRIGHT_TEXT)):
        return None
    keys = [json.dumps([c['category'], c['bbox'], c.get('text')], ensure_ascii=False) for c in cells]
    return cells if len(set(keys)) == len(keys) else None


PARTIAL_REGION = re.compile(r'\{"bbox": \[(\d+), (\d+), (\d+), (\d+)\], "category": "([A-Za-z-]+)"')


def upright_partial(native):
    """True when the unfinished primary already read text regions upright: turning cannot help."""
    content = native['choices'][0]['message']['content'] or ''
    text = [[int(n) for n in m[:4]] for m in PARTIAL_REGION.findall(content) if m[4] in UPRIGHT_TEXT]
    return bool(text) and not any(b[3] - b[1] >= 3 * (b[2] - b[0]) for b in text)


def retry_loop(native, image, recognize, turns_skipped=False):
    retry = native['loop_retry'] = {'trigger': retry_trigger(native), 'attempts': [], 'selected': None}
    if turns_skipped:
        retry['turns_skipped'] = 'upright_partial'
    for settings in LOOP_SETTINGS:
        attempt = {'penalties': settings, 'native': recognize_guarded(recognize, image, penalties=settings)}
        retry['attempts'].append(attempt)
        if loop_cells(attempt['native']) is None:
            continue
        retry['selected'] = len(retry['attempts']) - 1
        recognize_picture_text(attempt['native'], image)
        return True
    return False


def retry_rotated(native, image, recognize):
    retry = native['orientation_retry'] = {'trigger': retry_trigger(native), 'attempts': [], 'selected': None}
    for rotation, angle in ROTATIONS.items():
        turned = image.rotate(angle, expand=True)
        attempt = {'rotation': rotation, 'image_size': list(turned.size),
                   'native': recognize_guarded(recognize, turned)}
        retry['attempts'].append(attempt)
        choice = attempt['native']['choices'][0]
        if (choice['finish_reason'] != 'stop' or attempt['native'].get('local_stop_reason')
                or attempt['native'].get('client_error')):
            continue
        try:
            cells = json.loads(choice['message']['content'] or '')
        except json.JSONDecodeError:
            continue
        if (not isinstance(cells, list) or any(not isinstance(cell, dict) or 'bbox' not in cell
                                               or 'category' not in cell for cell in cells)
                or sideways_text(cells)):
            continue
        retry['selected'] = len(retry['attempts']) - 1
        recognize_picture_text(attempt['native'], turned)
        return True
    return False


def decode_native(engine, native):
    choice = native['choices'][0]
    retry = native.get('orientation_retry') or {}
    loop = native.get('loop_retry') or {}
    unfinished = retry_trigger(native) is not None
    if unfinished and loop.get('selected') is not None:
        # The unfinished primary and rejected attempts stay as evidence; the layout is the accepted retry.
        decoded = decode_native(engine, loop['attempts'][loop['selected']]['native'])
        decoded['loop_retry'] = loop['attempts'][loop['selected']]['penalties']
        return decoded
    if unfinished and retry.get('selected') is not None:
        # The truncated primary stays as evidence; the layout comes from the accepted turned page.
        attempt = retry['attempts'][retry['selected']]
        decoded = decode_native(engine, attempt['native'])
        size = attempt['image_size'][::-1]
        decoded['layout'] = [{**cell, 'bbox': unrotate_bbox(cell['bbox'], attempt['rotation'], size),
                              'rotated_bbox': cell['bbox'], 'page_rotation': attempt['rotation']}
                             for cell in decoded['layout']]
        decoded['coordinate_space'] = ('native model image pixels of the sent image; bboxes mapped back '
                                       'from the rotated retry recorded in rotated_bbox')
        return decoded
    text = choice['message']['content'] or ''
    if (not text.strip() or choice['finish_reason'] != 'stop' or native.get('local_stop_reason')
            or native.get('client_error')):
        reason = native.get('client_error') or native.get('local_stop_reason') or choice['finish_reason']
        raise ValueError(f'Empty or incomplete native model response ({reason}); inspect the retained page JSON')
    cells = json.loads(text)
    if not isinstance(cells, list) or any(not isinstance(cell, dict) or 'bbox' not in cell
                                          or 'category' not in cell for cell in cells):
        raise ValueError('dots.mocr did not return a native layout array')
    for region in native.get('picture_ocr', []):
        index = region['layout_index']
        if cells[index]['category'] != 'Picture' or cells[index]['bbox'] != region['bbox']:
            raise ValueError('Picture OCR does not match the primary layout')
        choice = region['native']['choices'][0]
        if choice['finish_reason'] != 'stop' or region['native'].get('local_stop_reason'):
            if native.get('picture_ocr_config', {}).get('failure_policy') == 'retain_unresolved':
                cells[index] = {**cells[index], 'ocr_issue': {
                    'stage': 'picture_ocr', 'reason': 'incomplete_response',
                    'finish_reason': choice['finish_reason']}}
                continue
            raise ValueError('Incomplete Picture OCR; inspect the retained native response')
        text = choice['message']['content'] or ''
        if text.strip():
            cells[index] = {**cells[index], 'text': text, 'text_source': 'picture_ocr'}
    return {'layout': cells, 'markdown': '\n\n'.join(cell['text'] for cell in cells if 'text' in cell),
            'coordinate_space': 'native model image pixels; image_size records the sent image'}


def parse_pages(selection, total):
    if selection is None:
        indices = list(range(total))
    else:
        indices = []
        for item in selection.split(','):
            bounds = [int(value) for value in item.split('-')]
            if len(bounds) not in (1, 2) or not 1 <= bounds[0] <= bounds[-1] <= total:
                raise ValueError(f'Physical pages must be between 1 and {total}')
            indices.extend(range(bounds[0] - 1, bounds[-1]))
    if not indices or len(set(indices)) != len(indices):
        raise ValueError('Physical pages must be nonempty and unique')
    return indices


def open_pdf(pdf):
    import pymupdf
    return pymupdf.open(str(pdf))


def render_page(page):
    from PIL import Image
    pixmap = page.get_pixmap(dpi=SETTINGS['image_dpi'], alpha=False)
    image = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
    scale = min(1.0, math.sqrt(SETTINGS['max_pixels'] / (image.width * image.height)))
    # Dots' processor uses a 28-pixel grid; keep the saved image in that coordinate space.
    width = max(28, int(image.width * scale / 28) * 28)
    height = max(28, int(image.height * scale / 28) * 28)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def load_page_orientation():
    from rapid_orientation import RapidOrientation
    from rapid_orientation.main import DEFAULT_PATH

    policy = {'package': 'rapid-orientation', 'version': '0.0.11', 'backend': 'CPUExecutionProvider',
              'model_sha256': '2f62c9bfb830a0b417241269fde7ef2d0ad5446c0ed2b8af33b1f6543545e8e2',
              'direction': 'counterclockwise', 'min_confidence': 0.85, 'score': 'minimum_crop_probability'}
    if version(policy['package']) != policy['version'] or hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest() != policy['model_sha256']:
        raise ValueError('Page orientation package/model does not match the pinned version')
    predictor = RapidOrientation()
    if predictor.session.session.get_providers() != [policy['backend']]:
        raise ValueError('Page orientation must run on CPU')
    def classify(image):
        angle, _ = predictor(image)
        # The public API returns elapsed time, not confidence; retain its vote and read the model scores.
        scores = predictor.session(predictor.preprocess(predictor.load_img(image)))[0]
        return angle, float(scores[:, predictor.labels.index(angle)].min())
    return classify, policy


def orient_page(image, predictor):
    predicted, confidence = predictor(image)
    predicted = int(predicted)
    if predicted not in (0, 90, 180, 270) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError('Invalid page orientation label')
    angle = predicted if confidence >= 0.85 else 0
    turned = image.rotate(angle, expand=True) if angle else image
    return turned, {'angle': angle, 'predicted_angle': predicted, 'confidence': confidence,
                    'image_size': list(turned.size)}


def unorient_bbox(bbox, angle, size):
    left, top, right, bottom = bbox
    width, height = size
    if angle == 180:
        return [width-right, height-bottom, width-left, height-top]
    return unrotate_bbox(bbox, 'ccw90' if angle == 90 else 'cw90', size) if angle else bbox


def parse_pdf(engine, pdf, output, selection=None, workers=None, rotation_retry=False, loop_retry=False,
              page_orientation=False):
    if engine != 'dotsmocr':
        raise ValueError('Only dots.mocr is supported')
    workers = workers if workers is not None else 16
    if not 1 <= workers <= 16:
        raise ValueError('dots.mocr supports 1 to 16 workers')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'pages').mkdir()
    (output / 'native').mkdir()
    started = time.perf_counter()
    with pdf.open('rb') as handle:
        checksum = hashlib.file_digest(handle, 'sha256').hexdigest()
    pages, order, markdowns = [], {}, {}
    manifest = {'engine': engine, 'source': str(pdf), 'source_sha256': checksum,
                'config': {**SETTINGS, 'workers': workers}, 'status': 'running', 'completed_pages': []}
    manifest['config']['sampling'] = DOTS_SAMPLING
    manifest['picture_ocr_config'] = json.loads(
        (LAB / 'config/dotsmocr_picture_ocr.json').read_text(encoding='utf-8'))
    if rotation_retry:
        manifest['config']['rotation_retry'] = {'trigger': 'length', 'rotations': list(ROTATIONS)}
    if loop_retry:
        # With the loop retry a client timeout is unfinished too and also tries the turns first.
        manifest['config']['loop_retry'] = {'triggers': ['length', 'timeout', 'tail_repetition'],
                                            'settings': list(LOOP_SETTINGS),
                                            'client_timeout_seconds': LAYOUT_TIMEOUT,
                                            'stream': True, 'continue_after_page_error': True,
                                            'tail_repetition': {'start_chars': 12000, 'repeats': 24,
                                                                'max_unit_chars': 256}}
    manifest['export'] = {'format': NATIVE_SIDECAR, 'native': 'native/page_NNNN.json',
                          'markdown': 'document.md'}

    def save():
        pages.sort(key=lambda page: order[page['page_number']])
        manifest['completed_pages'].sort(key=order.get)
        manifest['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        for name, value in [('run.json', manifest), ('document.json', {'pages': pages})]:
            write_json(output / name, value)
        (output / 'document.md').write_text('\n\n'.join(
            f'<!-- Physical page {page["page_number"]} -->\n\n'
            f'{page.get("markdown", markdowns.get(page["page_number"], ""))}'
            for page in pages), encoding='utf-8')

    def recognize_page(index, image, source_size, orientation):
        page = {'page_number': index + 1, 'image_size': list(source_size)}
        if orientation is not None:
            page['page_orientation'] = orientation
        name = f'page_{index + 1:04d}'
        path = output / 'pages' / f'{name}.json'
        raw, raw_path = {**page}, output / 'native' / f'{name}.json'
        try:
            # Without the loop retry a client timeout still fails the page, as before.
            raw['native'] = recognize_guarded(recognize, image) if loop_retry else recognize(image)
            write_json(raw_path, raw)
            try:
                unfinished = retry_trigger(raw['native']) is not None
                # With the loop retry an upright partial answer skips the turns (each would loop too).
                skip_turns = loop_retry and unfinished and upright_partial(raw['native'])
                if (rotation_retry and unfinished and not skip_turns
                        and retry_rotated(raw['native'], image, recognize)):
                    pass  # Picture OCR already ran on the accepted turned page.
                elif loop_retry and unfinished and retry_loop(raw['native'], image, recognize,
                                                              turns_skipped=rotation_retry and skip_turns):
                    pass  # Picture OCR already ran on the accepted upright retry.
                else:
                    recognize_picture_text(raw['native'], image)
            finally:
                write_json(raw_path, raw)
            page.update(decode_native(engine, raw['native']))
            if orientation and orientation['angle']:
                page['layout'] = [{**cell, 'oriented_bbox': cell['bbox'],
                                   'bbox': unorient_bbox(cell['bbox'], orientation['angle'], source_size)}
                                  for cell in page['layout']]
                page['coordinate_space'] = 'source image pixels; sent-image boxes retained in oriented_bbox'
            markdown = page.pop('markdown')
            markdowns[page['page_number']] = markdown
            write_json(path, page)
            (output / 'pages' / f'{name}.md').write_text(markdown, encoding='utf-8')
            return page, None
        except Exception as exc:
            page['error'] = f'{type(exc).__name__}: {exc}'
            if 'native' in raw:
                try:
                    write_json(raw_path, raw)
                except OSError:
                    page['native'] = raw['native']  # Keep it in document.json when the sidecar is unwritable.
            try:
                write_json(path, page)
            except OSError:
                pass  # The caller still retains this page record in document.json.
            return page, exc

    try:
        manifest['model'] = model_manifest(engine)
        predictor = None
        if page_orientation:
            predictor, manifest['config']['page_orientation'] = load_page_orientation()
        recognize, info = create_runtime(engine, loop_retry=True) if loop_retry else create_runtime(engine)
        manifest.update(info)
        with open_pdf(pdf) as document:
            indices = parse_pages(selection, len(document))
            order.update({index + 1: position for position, index in enumerate(indices)})
            manifest.update(source_pages=len(document), requested_pages=[index + 1 for index in indices])
            save()
            with (ThreadPoolExecutor(max_workers=workers) if workers > 1 else nullcontext()) as pool:
                remaining = iter(indices)
                jobs, failure, page_failure = [], None, None
                manifest['current_pages'] = []
                while True:
                    while failure is None and len(jobs) < workers:
                        index = next(remaining, None)
                        if index is None:
                            break
                        manifest['current_page'] = index + 1
                        print(f'Physical page {index + 1}: recognizing', flush=True)
                        # PyMuPDF stays on the caller thread; only recognition runs concurrently.
                        try:
                            image = render_page(document[index])
                            source_size = image.size
                            image.save(output / 'pages' / f'page_{index + 1:04d}.png')
                            orientation = None
                            if predictor is not None:
                                image, orientation = orient_page(image, predictor)
                        except Exception as exc:
                            failure = exc
                            manifest['current_page'] = index + 1
                            manifest.setdefault('failed_pages', []).append(index + 1)
                            break
                        jobs.append(pool.submit(recognize_page, index, image, source_size, orientation) if pool
                                    else recognize_page(index, image, source_size, orientation))
                        del image
                        manifest['current_pages'].append(index + 1)
                        try:
                            save()
                        except OSError as exc:
                            failure = failure or exc
                    if not jobs:
                        break
                    done = wait(jobs, return_when=FIRST_COMPLETED).done if pool else jobs[:]
                    for job in done:
                        jobs.remove(job)
                        page, error = job.result() if pool else job
                        pages.append(page)
                        number = page['page_number']
                        manifest['current_pages'].remove(number)
                        if error is None:
                            manifest['completed_pages'].append(number)
                            print(f'Physical page {number}: saved', flush=True)
                        else:
                            if loop_retry:
                                page_failure = page_failure or error
                            else:
                                failure = failure or error
                            manifest['current_page'] = number
                            manifest.setdefault('failed_pages', []).append(number)
                            print(f'Physical page {number}: failed: {error}', flush=True)
                        try:
                            save()
                        except OSError as exc:
                            failure = failure or exc
                if failure is not None or page_failure is not None:
                    raise failure or page_failure
                manifest.pop('current_page')
                manifest.pop('current_pages')
                save()
        manifest['status'] = 'complete'
    except BaseException as exc:
        manifest.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        save()
    print(f'Results: {output}', flush=True)


def check_runtime(engine):
    from PIL import Image, ImageDraw, ImageFont
    recognize, info = create_runtime(engine)
    with Image.new('RGB', (1680, 2380), 'white') as image:
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=48)
        for index, line in enumerate(('TEST OCR 123', 'Second paragraph 456', 'Final paragraph 789')):
            draw.text((120, 150 + index * 180), line, fill='black', font=font)
        native = recognize(image, max_tokens=SETTINGS['max_tokens'])
    json.dumps(native)  # Native page data must be serializable without discarding fields.
    decode_native(engine, native)
    if native.get('usage', {}).get('completion_tokens', 0) == 0:
        raise RuntimeError('Synthetic CUDA generation returned no tokens')
    print(json.dumps({'status': 'ready', **info, 'model': model_manifest(engine), 'config': SETTINGS,
                      'synthetic_cuda_forward': 'passed', 'synthetic_image_size': [1680, 2380],
                      'synthetic_native_export': 'passed',
                      'synthetic_usage': native.get('usage') if isinstance(native, dict) else None,
                      'documents_processed': 0}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', required=True, choices=MODELS)
    parser.add_argument('pdf', nargs='?', type=Path)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--pages', help='One-based physical pages, e.g. 6,8-9,45,74-75')
    parser.add_argument('--workers', type=int, choices=range(1, 17),
                        help='Concurrent pages: dots.mocr defaults to 16')
    parser.add_argument('--output', type=Path, help='New output directory; previous results are never overwritten')
    parser.add_argument('--rotation-retry', action='store_true',
                        help='dots.mocr: retry a token-limited page turned 90 degrees (at most twice)')
    parser.add_argument('--loop-retry', action='store_true',
                        help='dots.mocr: retry an unfinished (token limit or timeout) page upright with repetition penalties')
    parser.add_argument('--page-orientation', action='store_true',
                        help='dots.mocr: use the packaged PaddleClas four-way page classifier on CPU before OCR')
    args = parser.parse_args()
    if args.check:
        check_runtime(args.engine)
    else:
        if args.pdf is None:
            parser.error('PDF filename is required unless --check is used')
        pdf = args.pdf.resolve()
        if pdf.parent != Path('/data/input') or pdf.suffix.lower() != '.pdf' or not pdf.is_file():
            parser.error('PDF must be a file inside /data/input')
        output = args.output or Path('/data/results') / args.engine / pdf.stem / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        parse_pdf(args.engine, pdf, output, args.pages, args.workers, args.rotation_retry, args.loop_retry,
                  args.page_orientation)
