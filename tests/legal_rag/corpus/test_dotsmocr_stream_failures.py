"""Keep failed OCR stream evidence and propagate unresolved picture regions."""
import base64
from contextlib import nullcontext
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
spec = importlib.util.spec_from_file_location('client_review', ROOT / 'ocr/dotsmocr/scripts/new_ocr_pdf.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


def event(text='', finish=None):
    return b'data: ' + json.dumps({'id': 'test', 'choices': [{'delta': {'content': text},
                                                               'finish_reason': finish}]}).encode() + b'\n'


@pytest.mark.parametrize('reader', [client.read_layout_stream, client.read_picture_stream])
@pytest.mark.parametrize('problem', ['malformed', 'non_utf8', 'incomplete', 'server', 'invalid_event', 'invalid_content'])
def test_stream_retains_received_content_and_partial_bytes(reader, problem):
    partial = b'\xffpartial'
    def stream():
        yield event('retained')
        if problem == 'malformed':
            yield b'data: {"broken"\n'
        elif problem == 'non_utf8':
            yield b'data: \xff\n'
        elif problem == 'incomplete':
            raise http.client.IncompleteRead(partial, 10)
        elif problem == 'invalid_event':
            yield b'data: {"choices":[{"broken":1}]}\n'
        elif problem == 'invalid_content':
            yield b'data: {"choices":[{"delta":{"content":1}}]}\n'
        else:
            yield b'data: {"error":"failed"}\n'
    response = reader(stream())
    assert response['choices'][0]['message']['content'] == 'retained'
    assert response['stream_chunks'][0]['choices'][0]['delta']['content'] == 'retained'
    if problem == 'server':
        assert response['stream_chunks'][-1]['error'] == 'failed'
    assert response['client_error']
    assert response['choices'][0]['finish_reason'] != 'stop'
    if problem == 'incomplete':
        assert base64.b64decode(response['unparsed_sse_base64']) == partial
    if problem == 'malformed':
        assert base64.b64decode(response['unparsed_sse_base64']) == b'data: {"broken"\n'
    if problem == 'non_utf8':
        assert base64.b64decode(response['unparsed_sse_base64']) == b'data: \xff\n'


def test_picture_timeout_keeps_both_attempts_and_unresolved_region(tmp_path):
    (tmp_path / 'config').mkdir()
    settings = {'enabled': True, 'padding_pixels': 28, 'max_tokens': 512, 'temperature': 0,
                'prompt': 'OCR', 'failure_policy': 'retain_unresolved', 'recover_repetitions': True}
    (tmp_path / 'config/dotsmocr_picture_ocr.json').write_text(json.dumps(settings))
    native = {'choices': [{'message': {'content': json.dumps([{'category': 'Picture', 'bbox': [0, 0, 50, 50]}])},
                           'finish_reason': 'stop'}]}
    with patch.object(client, 'LAB', tmp_path), patch.object(client, 'request_image', side_effect=TimeoutError('timeout')):
        client.recognize_picture_text(native, Image.new('RGB', (100, 100)))
    assert len(native['picture_ocr'][0]['attempts']) == 2
    assert all(x['native']['client_error'] for x in native['picture_ocr'][0]['attempts'])
    assert 'ocr_issue' in client.decode_native('dotsmocr', native)['layout'][0]


def test_picture_stop_with_client_error_is_never_accepted(tmp_path):
    (tmp_path / 'config').mkdir()
    settings = {'enabled': True, 'padding_pixels': 28, 'max_tokens': 512, 'temperature': 0,
                'prompt': 'OCR', 'failure_policy': 'retain_unresolved', 'recover_repetitions': True}
    (tmp_path / 'config/dotsmocr_picture_ocr.json').write_text(json.dumps(settings))
    native = {'choices': [{'message': {'content': json.dumps([{'category': 'Picture', 'bbox': [0, 0, 50, 50]}])},
                           'finish_reason': 'stop'}]}
    partial = {'choices': [{'message': {'content': 'incomplete'}, 'finish_reason': 'stop'}], 'client_error': 'reset'}
    with patch.object(client, 'LAB', tmp_path), patch.object(client, 'request_image', return_value=partial) as request:
        client.recognize_picture_text(native, Image.new('RGB', (100, 100)))
    assert request.call_count == 2
    assert 'ocr_issue' in client.decode_native('dotsmocr', native)['layout'][0]


def test_unresolved_picture_survives_export_and_normalization(tmp_path):
    from legal_rag.corpus.ocr_runtime import _read_ocr_output
    from legal_rag.corpus.pdf_extraction import normalize_dotsmocr

    (tmp_path / 'config').mkdir()
    settings = {'enabled': True, 'padding_pixels': 28, 'max_tokens': 512, 'temperature': 0,
                'prompt': 'OCR', 'failure_policy': 'retain_unresolved', 'recover_repetitions': True}
    (tmp_path / 'config/dotsmocr_picture_ocr.json').write_text(json.dumps(settings))
    pdf = tmp_path / 'synthetic.pdf'
    pdf.write_bytes(b'%PDF-1.7 synthetic test')
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    cells = [{'category': 'Picture', 'bbox': [20, 30, 240, 70]},
             {'category': 'Text', 'bbox': [20, 100, 240, 140], 'text': 'preserved text'}]
    native = {'choices': [{'message': {'content': json.dumps(cells)}, 'finish_reason': 'stop'}]}
    model = {'repo': 'dots-studio/dots.mocr', 'revision': 'a' * 40, 'weights_sha256': {'model.safetensors': 'b' * 64}}
    output = tmp_path / 'output'
    with (patch.object(client, 'LAB', tmp_path), patch.object(client, 'model_manifest', return_value=model),
          patch.object(client, 'create_runtime', return_value=(lambda image: native, {})),
          patch.object(client, 'request_image', side_effect=TimeoutError('timeout')),
          patch.object(client, 'open_pdf', return_value=nullcontext([None])),
          patch.object(client, 'render_page', return_value=Image.new('RGB', (280, 420), 'white'))):
        client.parse_pdf('dotsmocr', pdf, output, workers=1)
    document, run = _read_ocr_output(output)
    result = normalize_dotsmocr(document, run, digest)
    assert 'picture_ocr_incomplete_response' in result['uncertainties']
    assert len(document['pages'][0]['native']['picture_ocr'][0]['attempts']) == 2
