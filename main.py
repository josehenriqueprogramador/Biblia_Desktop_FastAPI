from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
import pytesseract
import json
import datetime
import io
import os

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
static_dir = os.path.join(BASE_DIR, "static")
JSON_FILE = os.path.join(BASE_DIR, "versiculos.json")

if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)

if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        texto_extraido = pytesseract.image_to_string(image, lang="por")

        data_atual = datetime.date.today().isoformat()
        novo_registro = {"data_envio": data_atual, "texto": texto_extraido.strip()}

        with open(JSON_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)

        dados.append(novo_registro)

        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)

        return JSONResponse({"mensagem": "Imagem enviada e lida com sucesso!", "texto_extraido": texto_extraido.strip()})

    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)
