from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, os
from models import LIVROS_NOMES

app = FastAPI()

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
templates = Jinja2Templates(directory="templates")

# 🔹 Lista de versões disponíveis
versoes = sorted([f.replace('.json', '') for f in os.listdir(DATA_DIR) if f.endswith('.json')])
versao_padrao = "nvi"

def carregar_biblia(versao):
    """Carrega o arquivo JSON da versão especificada"""
    path = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    biblia = carregar_biblia(versao_padrao)
    livros = [(l['abbrev'], LIVROS_NOMES.get(l['abbrev'], l['abbrev'].capitalize())) for l in biblia]
    return templates.TemplateResponse(
        "livros.html",
        {
            "request": request,
            "livros": livros,
            "versao": versao_padrao,
            "versoes": versoes,
            "LIVROS_NOMES": LIVROS_NOMES
        }
    )

@app.get("/capitulos/{livro_abrev}", response_class=HTMLResponse)
async def capitulos(request: Request, livro_abrev: str):
    biblia = carregar_biblia(versao_padrao)
    livro = next((l for l in biblia if l.get('abbrev') == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    total = len(livro.get('chapters', []))
    return templates.TemplateResponse(
        "capitulos.html",
        {
            "request": request,
            "livro": livro,
            "total": total,
            "LIVROS_NOMES": LIVROS_NOMES
        }
    )

@app.get("/versiculos/{livro_abrev}/{capitulo}", response_class=HTMLResponse)
async def versiculos(request: Request, livro_abrev: str, capitulo: int):
    biblia = carregar_biblia(versao_padrao)
    livro = next((l for l in biblia if l.get('abbrev') == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    chapters = livro.get('chapters', [])
    if capitulo < 1 or capitulo > len(chapters):
        return HTMLResponse("Capítulo não encontrado", status_code=404)
    versiculos = chapters[capitulo - 1]
    return templates.TemplateResponse(
        "versiculos.html",
        {
            "request": request,
            "livro": livro,
            "capitulo": capitulo,
            "versiculos": versiculos,
            "LIVROS_NOMES": LIVROS_NOMES
        }
    )

# 🔹 Arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

