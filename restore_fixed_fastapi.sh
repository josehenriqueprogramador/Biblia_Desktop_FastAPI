#!/usr/bin/env bash
set -e

# Reescreve main.py e os templates
cat > main.py <<'PY'
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, json, io
from models import LIVROS_NOMES, carregar_biblia
from PIL import Image
import pytesseract

app = FastAPI()
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
templates = Jinja2Templates(directory="templates")

VERSOES = sorted([f.replace(".json", "") for f in os.listdir(DATA_DIR) if f.endswith(".json")])
DEFAULT_VERSAO = "nvi"

def obter_biblia(versao: str = DEFAULT_VERSAO):
    path = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(path):
        return []
    try:
        return carregar_biblia(path)
    except Exception:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

def versao_atual_from_request(request: Request):
    return request.query_params.get("versao", DEFAULT_VERSAO)

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/livros")

@app.get("/livros", response_class=HTMLResponse)
async def livros(request: Request):
    versao = versao_atual_from_request(request)
    biblia = obter_biblia(versao)
    return templates.TemplateResponse("livros.html", {
        "request": request,
        "biblia": biblia,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": VERSOES,
        "versao": versao
    })

@app.get("/capitulos/{livro_abrev}", response_class=HTMLResponse)
async def capitulos(request: Request, livro_abrev: str):
    versao = versao_atual_from_request(request)
    biblia = obter_biblia(versao)
    livro = next((l for l in biblia if getattr(l, "abrev", l.get("abbrev", "")) == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    total = len(getattr(livro, "capitulos", livro.get("chapters", [])))
    return templates.TemplateResponse("capitulos.html", {
        "request": request,
        "livro": livro,
        "total": total,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": VERSOES,
        "versao": versao
    })

@app.get("/versiculos/{livro_abrev}/{capitulo}", response_class=HTMLResponse)
async def versiculos(request: Request, livro_abrev: str, capitulo: int):
    versao = versao_atual_from_request(request)
    biblia = obter_biblia(versao)
    livro = next((l for l in biblia if getattr(l, "abrev", l.get("abbrev", "")) == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    chapters = getattr(livro, "capitulos", livro.get("chapters", []))
    if capitulo < 1 or capitulo > len(chapters):
        return HTMLResponse("Capítulo não encontrado", status_code=404)
    versiculos = chapters[capitulo - 1]
    return templates.TemplateResponse("versiculos.html", {
        "request": request,
        "livro": livro,
        "capitulo": capitulo,
        "versiculos": versiculos,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": VERSOES,
        "versao": versao
    })

if os.path.isdir(os.path.join(BASE_DIR, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
PY

echo "Arquivos restaurados. Agora rode:"
echo "uvicorn main:app --reload"
