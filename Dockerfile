# Use uma imagem oficial do Python
FROM python:3.12-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Copia apenas requirements primeiro para aproveitar cache do Docker
COPY requirements.txt .

# Instala dependências do Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copia todo o restante do código
COPY . .

# Expor a porta usada pelo FastAPI
EXPOSE 5000

# Comando para iniciar o servidor Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
