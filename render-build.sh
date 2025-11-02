#!/usr/bin/env bash
# Instala dependências do sistema antes do build
apt-get update && \
apt-get install -y tesseract-ocr libtesseract-dev libleptonica-dev && \
echo "✅ Tesseract instalado com sucesso!"

# Instala dependências do Python
pip install -r requirements.txt
