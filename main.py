from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pytesseract
from PIL import Image
import json
import os

app = FastAPI()

# Configura pastas estáticas e templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DATA_PATH = "data"

# 🏠 Página principal — lista os livros da Bíblia
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    versions = [f.replace(".json", "") for f in os.listdir(DATA_PATH) if f.endswith(".json")]
    with open(os.path.join(DATA_PATH, "acf.json"), "r", encoding="utf-8") as f:
        bible_data = json.load(f)

    books = list(bible_data.keys())
    return templates.TemplateResponse("livros.html", {"request": request, "books": books, "versions": versions})


# 📄 Página para envio de imagem e OCR
@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "texto_extraido": None})


# 🧠 OCR — processa imagem e mostra texto extraído
@app.post("/ocr", response_class=HTMLResponse)
async def process_image(request: Request, file: UploadFile = File(...)):
    try:
        image = Image.open(file.file)
        text = pytesseract.image_to_string(image, lang="por")
        return templates.TemplateResponse("upload.html", {"request": request, "texto_extraido": text})
    except Exception as e:
        return templates.TemplateResponse("upload.html", {"request": request, "texto_extraido": f"Erro ao processar imagem: {e}"})


# ✅ Exemplo de rota para mudar de versão (mantendo lógica anterior)
@app.get("/versao/{versao}", response_class=HTMLResponse)
async def mudar_versao(request: Request, versao: str):
    version_file = os.path.join(DATA_PATH, f"{versao}.json")
    if not os.path.exists(version_file):
        return HTMLResponse(content=f"<h3>Versão {versao} não encontrada</h3>", status_code=404)
    with open(version_file, "r", encoding="utf-8") as f:
        bible_data = json.load(f)
    books = list(bible_data.keys())
    return templates.TemplateResponse("livros.html", {"request": request, "books": books, "versions": os.listdir(DATA_PATH)})
