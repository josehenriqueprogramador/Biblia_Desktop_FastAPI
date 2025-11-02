from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
import pytesseract
import json
import datetime
import io
import os
import re

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

JSON_FILE = "leituras.json"


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Página inicial com formulário de upload"""
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "mensagem": None, "texto_extraido": None},
    )


@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...)):
    """Lê a imagem enviada, faz OCR e salva no JSON"""
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    texto_extraido = pytesseract.image_to_string(image, lang="por").strip()

    # tenta extrair pares "01/11 - João 3"
    padrao = re.compile(r"(\d{1,2}/\d{1,2})\s*[-–]\s*([A-Za-zÀ-ÖØ-öø-ÿ0-9\s:]+)")
    ano_atual = datetime.date.today().year
    leituras_extraidas = []

    for data, ref in re.findall(padrao, texto_extraido):
        try:
            d, m = map(int, data.split("/"))
            data_iso = f"{ano_atual}-{m:02d}-{d:02d}"
            leituras_extraidas.append({"data": data_iso, "referencia": ref.strip()})
        except:
            continue

    # Carrega leituras anteriores
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except FileNotFoundError:
        dados = []

    # adiciona novas
    dados.extend(leituras_extraidas)

    # salva
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "mensagem": f"Imagem processada! {len(leituras_extraidas)} leitura(s) reconhecida(s).",
            "texto_extraido": texto_extraido,
        },
    )


@app.get("/versiculo-hoje", response_class=HTMLResponse)
def versiculo_hoje(request: Request):
    """Mostra a leitura correspondente à data atual"""
    hoje = datetime.date.today().isoformat()

    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except FileNotFoundError:
        dados = []

    leitura = next((d for d in dados if d["data"] == hoje), None)

    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "mensagem": f"Leitura de hoje ({hoje})",
            "texto_extraido": leitura["referencia"]
            if leitura
            else "Nenhuma leitura programada para hoje.",
        },
    )

