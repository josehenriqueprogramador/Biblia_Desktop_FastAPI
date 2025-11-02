# Usa uma imagem base leve do Python
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Instala dependências de sistema (Tesseract + libs para manipulação de imagens)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    libtesseract-dev \
    libleptonica-dev \
    poppler-utils \
    libgl1 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . .

# Instala dependências Python necessárias (FastAPI stack + OCR)
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    jinja2 \
    python-multipart \
    pillow \
    pytesseract

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
