from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from models import carregar_biblia, LIVROS_NOMES

# ========================
# CONFIGURAÇÃO BÁSICA
# ========================
app = FastAPI(title="📘 Bíblia Desktop - FastAPI")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Monta a pasta /static para servir Bootstrap localmente
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Configura templates Jinja2
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ========================
# CARREGA TODAS AS VERSÕES
# ========================
def carregar_versoes():
    versoes = {}
    for nome_arquivo in os.listdir(DATA_DIR):
        if nome_arquivo.endswith(".json"):
            versao_nome = nome_arquivo.replace(".json", "")
            caminho = os.path.join(DATA_DIR, nome_arquivo)
            versoes[versao_nome] = carregar_biblia(caminho)
    return versoes

BIBLIAS = carregar_versoes()
VERSOES_DISPONIVEIS = list(BIBLIAS.keys())

# ========================
# ROTAS PRINCIPAIS
# ========================

@app.get("/", response_class=HTMLResponse)
def livros(request: Request, versao: str = VERSOES_DISPONIVEIS[0]):
    livros = BIBLIAS[versao]
    return templates.TemplateResponse("livros.html", {
        "request": request,
        "livros": livros,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": VERSOES_DISPONIVEIS,
        "versao": versao
    })


@app.get("/livro/{livro_abrev}", response_class=HTMLResponse)
def capitulos(request: Request, livro_abrev: str, versao: str = VERSOES_DISPONIVEIS[0]):
    livros = BIBLIAS[versao]
    livro = next((l for l in livros if l.abrev == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)

    total = len(livro.capitulos)
    return templates.TemplateResponse("capitulos.html", {
        "request": request,
        "livro": livro,
        "total": total,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": VERSOES_DISPONIVEIS,
        "versao": versao
    })


@app.get("/livro/{livro_abrev}/{capitulo}", response_class=HTMLResponse)
def versiculos(request: Request, livro_abrev: str, capitulo: int, versao: str = VERSOES_DISPONIVEIS[0]):
    livros = BIBLIAS[versao]
    livro = next((l for l in livros if l.abrev == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)

    cap = livro.get_capitulo(capitulo)
    if not cap:
        return HTMLResponse("Capítulo não encontrado", status_code=404)

    versiculos = [v.texto for v in cap.versiculos]
    return templates.TemplateResponse("versiculos.html", {
        "request": request,
        "livro": livro,
        "capitulo": capitulo,
        "versiculos": versiculos,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": VERSOES_DISPONIVEIS,
        "versao": versao
    })
