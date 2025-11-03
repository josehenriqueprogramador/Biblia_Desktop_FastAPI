# --- cole o código Python aqui ---
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import pytesseract
import os
import io
import json
from datetime import date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "data/uploads"
NVI_DIR = "data/NVI"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(NVI_DIR, exist_ok=True)

@app.get("/")
def index():
    return {"mensagem": "Envie uma imagem com as leituras (ex: 01/11 - João 1)."}

@app.post("/upload")
async def upload_imagem(file: UploadFile = File(...)):
    try:
        conteudo = await file.read()
        imagem = Image.open(io.BytesIO(conteudo))
        texto_extraido = pytesseract.image_to_string(imagem, lang="por")
        caminho_txt = os.path.join(UPLOAD_DIR, f"{file.filename}.txt")
        with open(caminho_txt, "w", encoding="utf-8") as f:
            f.write(texto_extraido)
        return {
            "mensagem": "Imagem enviada e lida com sucesso!",
            "arquivo": file.filename,
            "texto_extraido": texto_extraido
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": f"Falha ao processar imagem: {str(e)}"})

@app.get("/versiculo-hoje")
def versiculo_hoje():
    data_hoje = date.today().strftime("%d/%m")
    leitura = None
    for nome_arquivo in os.listdir(UPLOAD_DIR):
        caminho = os.path.join(UPLOAD_DIR, nome_arquivo)
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read()
            if data_hoje in conteudo:
                leitura = conteudo.split(data_hoje, 1)[1].strip().split("\n")[0]
                break
    if not leitura:
        return {"data": str(date.today()), "texto": None, "info": "Nenhuma leitura encontrada"}
    leitura_formatada = leitura.replace("*", "").replace("+", "").replace("«", "").replace("»", "").strip()
    return {"data": str(date.today()), "texto": leitura_formatada, "info": "Leitura encontrada com sucesso"}
