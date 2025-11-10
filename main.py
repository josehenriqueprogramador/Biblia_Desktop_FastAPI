from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import json, os, io
import enviar_leitura_whatsapp
from models import LIVROS_NOMES

# -------------------------------------------------------
# Configuração base
# -------------------------------------------------------
app = FastAPI()
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
LEITURAS_DIR = os.path.join(BASE_DIR, "leituras")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(LEITURAS_DIR, exist_ok=True)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# -------------------------------------------------------
# CORS (para o app Kivy ou outro cliente)
# -------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # em produção, restrinja
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------
# Funções auxiliares
# -------------------------------------------------------
def listar_versoes():
    return sorted([f.replace(".json", "") for f in os.listdir(DATA_DIR) if f.endswith(".json")])

def carregar_biblia(versao):
    caminho = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Versão {versao} não encontrada.")
    with open(caminho, "r", encoding="utf-8-sig") as f:
        return json.load(f)

# -------------------------------------------------------
# Middleware estático
# -------------------------------------------------------
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# -------------------------------------------------------
# Variável global simples (substitui session do Flask)
# -------------------------------------------------------
versao_atual = "nvi"

# -------------------------------------------------------
# Rotas HTML existentes
# -------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return RedirectResponse(url=request.url_for("livros"))

@app.get("/livros", response_class=HTMLResponse)
async def livros(request: Request):
    biblia = carregar_biblia(versao_atual)
    return templates.TemplateResponse("livros.html", {
        "request": request,
        "livros": biblia,
        "versao": versao_atual,
        "versoes": listar_versoes(),
        "LIVROS_NOMES": LIVROS_NOMES
    })

@app.get("/trocar_versao", response_class=HTMLResponse)
async def trocar_versao(request: Request, versao: str = "nvi"):
    global versao_atual
    if versao in listar_versoes():
        versao_atual = versao
    return RedirectResponse(url=request.url_for("livros"))

@app.get("/capitulos/{livro_abrev}", response_class=HTMLResponse)
async def capitulos(request: Request, livro_abrev: str):
    biblia = carregar_biblia(versao_atual)
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    total = len(livro.get("chapters", []))
    return templates.TemplateResponse("capitulos.html", {
        "request": request,
        "livro": livro,
        "total": total,
        "versao": versao_atual,
        "versoes": listar_versoes(),
        "LIVROS_NOMES": LIVROS_NOMES
    })

# -------------------------------------------------------
# API JSON (para consumo pelo Kivy ou outros)
# -------------------------------------------------------

@app.get("/api/versions")
async def api_versions():
    """Lista as versões de Bíblia disponíveis"""
    return {"versions": listar_versoes()}

@app.get("/api/books")
async def api_books(versao: str = Query(...)):
    """Retorna todos os livros de uma versão"""
    try:
        biblia = carregar_biblia(versao)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Versão não encontrada")

    books = [{"abbrev": l.get("abbrev"), "name": l.get("name", l.get("abbrev"))} for l in biblia]
    return {"books": books}

@app.get("/api/chapters")
async def api_chapters(versao: str = Query(...), book: str = Query(...)):
    """Retorna os capítulos de um livro"""
    try:
        biblia = carregar_biblia(versao)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Versão não encontrada")

    livro = next((l for l in biblia if l.get("abbrev") == book), None)
    if not livro:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    total = len(livro.get("chapters", []))
    return {"book": book, "chapters": list(range(1, total + 1))}

@app.get("/api/verses")
async def api_verses(versao: str = Query(...), book: str = Query(...), chapter: int = Query(...)):
    """Retorna os versículos de um capítulo"""
    try:
        biblia = carregar_biblia(versao)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Versão não encontrada")

    livro = next((l for l in biblia if l.get("abbrev") == book), None)
    if not livro:
        raise HTTPException(status_code=404, detail="Livro não encontrado")

    chapters = livro.get("chapters", [])
    if chapter < 1 or chapter > len(chapters):
        raise HTTPException(status_code=400, detail="Capítulo inválido")

    verses = chapters[chapter - 1]
    enumerated = [{"index": i + 1, "text": v} for i, v in enumerate(verses)]
    return {"book": book, "chapter": chapter, "verses": enumerated}

