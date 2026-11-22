FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# OCR(한국어 포함)·이미지 처리·PDF 래스터화용 시스템 패키지.
# 폐쇄망에서는 내부 미러를 사용한다.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo zlib1g libxml2 libxslt1.1 \
        tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY . .

# Render Secret File(/etc/secrets/...)을 읽기 위해 appuser를 GID 1000 그룹의 보조 구성원으로 등록한다 (TK-79)
# RapidOCR 한국어 ONNX 모델을 빌드 시점에 미리 내려받아 무네트워크 기동을 보장한다 (TK-227)
RUN python -c "import numpy as np; from rapidocr import RapidOCR, LangRec, OCRVersion, ModelType; r = RapidOCR(params={'Rec.lang_type': LangRec.KOREAN, 'Rec.ocr_version': OCRVersion.PPOCRV5, 'Rec.model_type': ModelType.MOBILE}); r(np.full((32, 128, 3), 255, dtype=np.uint8), use_det=False, use_cls=False, use_rec=True)" \
    && (getent group 1000 || groupadd -g 1000 rendersecrets) \
    && useradd -m -u 10001 -G 1000 appuser \
    && mkdir -p /data && chown -R appuser:appuser /app /data
USER appuser

ENV LV_DATA_DIR=/data \
    LV_OCR_LANG=kor+eng \
    LV_REQUIRE_OCR=1 \
    LV_OCR_FALLBACK_ENGINE=rapidocr \
    LV_OCR_FALLBACK_MODE=auto

RUN python -m scripts.check_ocr_runtime
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://localhost:'+os.getenv('PORT','8000')+'/api/health', timeout=4)" || exit 1

CMD ["python", "-m", "scripts.start_server"]
