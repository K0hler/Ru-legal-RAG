FROM vllm/vllm-openai:v0.11.0@sha256:d8d39b59e909d2378ac4feeb191f7e7b6f1342477dc66b7c47cec89e9985ad8a

COPY requirements.lock /tmp/dots-requirements.lock
RUN python3 -m pip install --no-cache-dir --no-deps -r /tmp/dots-requirements.lock
COPY scripts/new_ocr_pdf.py /opt/dotsmocr/scripts/new_ocr_pdf.py
COPY scripts/verify_model.py /opt/dotsmocr/scripts/verify_model.py
COPY config /opt/dotsmocr/config

ENV VLLM_PLUGINS=""
ENTRYPOINT ["python3", "/opt/dotsmocr/scripts/verify_model.py", "/data/model", "/opt/dotsmocr/config/new_ocr_models.json", "--"]
