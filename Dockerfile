# ----------------------
# Imagem base
# ----------------------
FROM python:3.12-slim

# ----------------------
# Variáveis de ambiente
# ----------------------
ENV PYTHONUNBUFFERED=1
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata/

# ----------------------
# Instala pacotes do sistema
# ----------------------
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ----------------------
# Diretório da aplicação
# ----------------------
WORKDIR /app

# ----------------------
# Copia arquivos do projeto
# ----------------------
COPY . /app

# ----------------------
# Instala dependências Python
# ----------------------
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------
# Expõe porta
# ----------------------
EXPOSE 5000

# ----------------------
# Comando de inicialização
# ----------------------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
