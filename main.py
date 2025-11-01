import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models import LIVROS_NOMES

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
versoes = sorted([f.replace(".json", "") for f in os.listdir(DATA_DIR) if f.endswith(".json")])
VERSAO_PADRAO = "nvi"  # você pode alterar para a versão que quiser

templates = Jinja2Templates(directory="templates")


# Carrega a Bíblia JSON de uma versão
def carregar_biblia(versao: str):
    path = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


@app.get("/")
def index():
    return RedirectResponse(url="/livros")


@app.get("/livros")
def livros(request: Request, versao: str = VERSAO_PADRAO):
    biblia = carregar_biblia(versao)
    return templates.TemplateResponse(
        "livros.html",
        {
            "request": request,
            "livros": biblia,
            "LIVROS_NOMES": LIVROS_NOMES,
            "versao": versao,
            "versoes": versoes,
        },
    )


@app.get("/livro/{livro_abrev}", name="capitulos")
def capitulos(request: Request, livro_abrev: str, versao: str = VERSAO_PADRAO):
    biblia = carregar_biblia(versao)
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        return templates.TemplateResponse(
            "erro.html",
            {"request": request, "mensagem": "Livro não encontrado"},
            status_code=404,
        )
    total = len(livro.get("chapters", []))
    return templates.TemplateResponse(
        "capitulos.html",
        {
            "request": request,
            "livro": livro,
            "total": total,
            "LIVROS_NOMES": LIVROS_NOMES,
            "versao": versao,
        },
    )


@app.get("/versiculos/{livro_abrev}/{capitulo}")
def versiculos(request: Request, livro_abrev: str, capitulo: int, versao: str = VERSAO_PADRAO):
    biblia = carregar_biblia(versao)
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        return templates.TemplateResponse(
            "erro.html",
            {"request": request, "mensagem": "Livro não encontrado"},
            status_code=404,
        )
    chapters = livro.get("chapters", [])
    if capitulo < 1 or capitulo > len(chapters):
        return templates.TemplateResponse(
            "erro.html",
            {"request": request, "mensagem": "Capítulo não encontrado"},
            status_code=404,
        )
    versiculos = chapters[capitulo - 1]
    return templates.TemplateResponse(
        "versiculos.html",
        {
            "request": request,
            "livro": livro,
            "capitulo": capitulo,
            "versiculos": versiculos,
            "LIVROS_NOMES": LIVROS_NOMES,
            "versao": versao,
        },
    )

