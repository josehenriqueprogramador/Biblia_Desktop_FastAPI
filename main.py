from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pytesseract
from PIL import Image
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
def home(request: Request):
    versoes = ["almeida", "nvi"]
    versao = request.query_params.get("versao", versoes[0])
    return templates.TemplateResponse("upload.html", {"request": request, "versoes": versoes, "versao": versao})


@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...)):
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

        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "mensagem": "Imagem enviada e lida com sucesso!",
                "texto_extraido": texto_extraido.strip(),
                "data": data_atual,
                "versoes": ["almeida", "nvi"],
                "versao": request.query_params.get("versao", "almeida")
            },
        )

    except Exception as e:
        return HTMLResponse(f"<h3>Erro ao processar imagem: {str(e)}</h3>", status_code=500)


@app.get("/versiculo-hoje", response_class=HTMLResponse)
def versiculo_hoje(request: Request):
    try:
        hoje = datetime.date.today().isoformat()
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)

        versiculos_hoje = [d for d in dados if d.get("data_envio") == hoje]

        texto = "\n\n".join(v["texto"] for v in versiculos_hoje) if versiculos_hoje else "Nenhum versículo registrado para hoje."

        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "mensagem": f"Versículos do dia {hoje}",
                "texto_extraido": texto,
                "data": hoje,
                "versoes": ["almeida", "nvi"],
                "versao": request.query_params.get("versao", "almeida")
            },
        )

    except Exception as e:
        return HTMLResponse(f"<h3>Erro ao buscar versículo: {str(e)}</h3>", status_code=500)


@app.get("/listar_leituras", response_class=HTMLResponse)
def listar_leituras(request: Request):
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)

        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "mensagem": f"Todas as leituras ({len(dados)})",
                "todas_leituras": dados,
                "versoes": ["almeida", "nvi"],
                "versao": request.query_params.get("versao", "almeida")
            },
        )
    except Exception as e:
        return HTMLResponse(f"<h3>Erro ao listar leituras: {str(e)}</h3>", status_code=500)
