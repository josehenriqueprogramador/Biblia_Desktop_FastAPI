from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, json
from models import LIVROS_NOMES, carregar_biblia

app = FastAPI()
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
templates = Jinja2Templates(directory="templates")

# Lista as versões disponíveis
VERSOES = sorted([f.replace(".json", "") for f in os.listdir(DATA_DIR) if f.endswith(".json")])
DEFAULT_VERSAO = "nvi"

def obter_biblia(versao: str = DEFAULT_VERSAO):
    """Carrega a Bíblia de um JSON com suporte a BOM UTF-8."""
    path = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

@app.get("/", response_class=HTMLResponse)
async def index():
    """Redireciona para a lista de livros."""
    return RedirectResponse(url="/livros")

@app.get("/livros", response_class=HTMLResponse)
async def livros(request: Request, versao: str = DEFAULT_VERSAO):
    """Mostra a lista de livros."""
    biblia = obter_biblia(versao)
    livros = []
    for livro in biblia:
        abrev = livro.get("abbrev")
        nome = LIVROS_NOMES.get(abrev, livro.get("name", abrev))
        livros.append({"abrev": abrev, "nome": nome})
    return templates.TemplateResponse("livros.html", {
        "request": request,
        "livros": livros,
        "versoes": VERSOES,
        "versao": versao
    })

@app.get("/capitulos/{livro_abrev}", response_class=HTMLResponse)
async def capitulos(request: Request, livro_abrev: str, versao: str = DEFAULT_VERSAO):
    """Mostra os capítulos do livro."""
    biblia = obter_biblia(versao)
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    total = len(livro.get("chapters", []))
    nome = LIVROS_NOMES.get(livro_abrev, livro.get("name", livro_abrev))
    return templates.TemplateResponse("capitulos.html", {
        "request": request,
        "livro": livro,
        "nome": nome,
        "total": total,
        "versoes": VERSOES,
        "versao": versao
    })

@app.get("/versiculos/{livro_abrev}/{int_capitulo}", response_class=HTMLResponse)
async def versiculos(request: Request, livro_abrev: str, int_capitulo: int, versao: str = DEFAULT_VERSAO):
    """Mostra os versículos do capítulo."""
    biblia = obter_biblia(versao)
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    chapters = livro.get("chapters", [])
    if int_capitulo < 1 or int_capitulo > len(chapters):
        return HTMLResponse("Capítulo não encontrado", status_code=404)
    versiculos = chapters[int_capitulo - 1]
    nome = LIVROS_NOMES.get(livro_abrev, livro.get("name", livro_abrev))
    return templates.TemplateResponse("versiculos.html", {
        "request": request,
        "livro": livro,
        "nome": nome,
        "capitulo": int_capitulo,
        "versiculos": versiculos,
        "versoes": VERSOES,
        "versao": versao
    })

if os.path.isdir(os.path.join(BASE_DIR, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
