#!/usr/bin/env python3
# main.py — FastAPI + HTML + API JSON (pronto para Termux)
import os
import tempfile
from urllib.parse import urlparse
from typing import List, Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import json
import io
import sys
import enviar_leitura_whatsapp
from models import LIVROS_NOMES

# ---------------------------
# Paths / dirs
# ---------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
LEITURAS_DIR = os.path.join(BASE_DIR, "leituras")
VERSAO_FILE = os.path.join(DATA_DIR, "versao_atual.txt")

# Ensure required dirs exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(LEITURAS_DIR, exist_ok=True)
# templates and static should already exist in your repo; create if missing
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ---------------------------
# App / templates / static
# ---------------------------
app = FastAPI(title="Bíblia - HTML + API")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# mount static (serve css/js/images)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---------------------------
# CORS (dev default; override via ALLOWED_ORIGINS env)
# ---------------------------
try:
    allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
    if allowed_origins_env:
        import ast
        ALLOWED_ORIGINS = ast.literal_eval(allowed_origins_env)
    else:
        ALLOWED_ORIGINS = ["*"]
except Exception:
    ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Helpers (JSON load, versões)
# ---------------------------
def listar_versoes() -> List[str]:
    """
    Lista arquivos .json em DATA_DIR -> retorna ['nvi', 'acf', ...]
    """
    try:
        return sorted([f.replace(".json", "") for f in os.listdir(DATA_DIR) if f.endswith(".json")])
    except FileNotFoundError:
        return []

def carregar_biblia_raw(versao: str):
    """
    Carrega o JSON bruto (lista de livros) do arquivo data/<versao>.json.
    Retorna None se não existir.
    """
    caminho = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(caminho):
        return None
    with open(caminho, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def get_versao_atual(default: str = "nvi") -> str:
    """Lê versão atual de arquivo (persistente)."""
    try:
        if os.path.exists(VERSAO_FILE):
            with open(VERSAO_FILE, "r", encoding="utf-8") as f:
                v = f.read().strip()
                return v or default
    except Exception:
        pass
    return default

def set_versao_atual(valor: str) -> None:
    """Salva versão atual de forma atômica."""
    os.makedirs(os.path.dirname(VERSAO_FILE), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(VERSAO_FILE))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(valor)
        os.replace(tmp_path, VERSAO_FILE)
    except Exception:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        raise

def safe_redirect_target(request: Request, target: Optional[str]) -> str:
    """
    Permite apenas caminhos relativos ou mesmos-host full URLs.
    Caso contrário retorna /livros.
    """
    if not target:
        return request.url_for("livros")
    parsed = urlparse(target)
    if not parsed.netloc:
        return target
    request_host = request.url.hostname
    if parsed.hostname == request_host:
        return target
    return request.url_for("livros")

# ---------------------------
# HTML Routes (usam templates existentes)
# ---------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return RedirectResponse(url=request.url_for("livros"))

@app.get("/livros", response_class=HTMLResponse)
async def livros(request: Request):
    versao = get_versao_atual()
    biblia = carregar_biblia_raw(versao) or []
    return templates.TemplateResponse("livros.html", {
        "request": request,
        "livros": biblia,
        "versao": versao,
        "versoes": listar_versoes(),
        "LIVROS_NOMES": LIVROS_NOMES
    })

@app.get("/capitulos/{livro_abrev}", response_class=HTMLResponse)
async def capitulos(request: Request, livro_abrev: str):
    versao = get_versao_atual()
    biblia = carregar_biblia_raw(versao) or []
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    total = len(livro.get("chapters", []))
    return templates.TemplateResponse("capitulos.html", {
        "request": request,
        "livro": livro,
        "total": total,
        "versao": versao,
        "versoes": listar_versoes(),
        "LIVROS_NOMES": LIVROS_NOMES
    })

@app.get("/versiculos/{livro_abrev}/{capitulo}", response_class=HTMLResponse)
async def versiculos(request: Request, livro_abrev: str, capitulo: int):
    versao = get_versao_atual()
    biblia = carregar_biblia_raw(versao) or []
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    chapters = livro.get("chapters", [])
    if capitulo < 1 or capitulo > len(chapters):
        return HTMLResponse("Capítulo não encontrado", status_code=404)
    versiculos = chapters[capitulo - 1]
    return templates.TemplateResponse("versiculos.html", {
        "request": request,
        "livro": livro,
        "capitulo": capitulo,
        "versiculos": versiculos,
        "versao": versao,
        "versoes": listar_versoes(),
        "LIVROS_NOMES": LIVROS_NOMES
    })

# ---------------------------
# Trocar versão (POST e GET compatível)
# ---------------------------
@app.post("/trocar_versao", response_class=HTMLResponse)
async def trocar_versao_post(request: Request, versao: str = Form(...), voltar_para: Optional[str] = Form(None)):
    versoes = listar_versoes()
    if versao not in versoes:
        raise HTTPException(status_code=400, detail="Versão inválida.")
    set_versao_atual(versao)
    target = safe_redirect_target(request, voltar_para)
    return RedirectResponse(url=target)

@app.get("/trocar_versao", response_class=HTMLResponse)
async def trocar_versao_get(request: Request, versao: str = "nvi"):
    if versao in listar_versoes():
        set_versao_atual(versao)
    referer = request.headers.get("referer")
    target = safe_redirect_target(request, referer)
    return RedirectResponse(url=target)

# ---------------------------
# Upload (async-safe)
# ---------------------------

@app.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/upload", response_class=HTMLResponse)
async def upload_cronograma(request: Request, file: UploadFile = File(...)):
    try:
        conteudo = await file.read()
        filename = os.path.basename(file.filename)
        caminho = os.path.join(UPLOADS_DIR, filename)
        with open(caminho, "wb") as f:
            f.write(conteudo)
        mensagem = f"Imagem '{filename}' enviada com sucesso!"
    except Exception as e:
        mensagem = f"Erro ao processar a imagem: {e}"
    return templates.TemplateResponse("upload.html", {"request": request, "mensagem": mensagem})

# ---------------------------
# API JSON (para app mobile)
# ---------------------------
@app.get("/api/versoes")
def api_versoes():
    return {"versoes": listar_versoes()}

@app.get("/api/livros/{versao}")
def api_livros(versao: str):
    biblia = carregar_biblia_raw(versao)
    if biblia is None:
        raise HTTPException(status_code=404, detail="Versão não encontrada")
    return {"versao": versao, "livros": biblia}

@app.get("/api/capitulos/{versao}/{livro_abrev}")
def api_capitulos(versao: str, livro_abrev: str):
    biblia = carregar_biblia_raw(versao)
    if biblia is None:
        raise HTTPException(status_code=404, detail="Versão não encontrada")
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return {"versao": versao, "livro": livro_abrev, "capitulos": len(livro.get("chapters", []))}

@app.get("/api/versiculos/{versao}/{livro_abrev}/{capitulo}")
def api_versiculos(versao: str, livro_abrev: str, capitulo: int):
    biblia = carregar_biblia_raw(versao)
    if biblia is None:
        raise HTTPException(status_code=404, detail="Versão não encontrada")
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    chapters = livro.get("chapters", [])
    if capitulo < 1 or capitulo > len(chapters):
        raise HTTPException(status_code=404, detail="Capítulo inválido")
    return {"versao": versao, "livro": livro_abrev, "capitulo": capitulo, "versiculos": chapters[capitulo - 1]}

# ---------------------------
# Rotas de execução / integração (mantive comportamento)
# ---------------------------
@app.get("/enviar_versiculo")
def enviar_versiculo():
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer
    try:
        enviar_leitura_whatsapp.main()
    except Exception as e:
        print("❌ Erro:", e)
    finally:
        sys.stdout = old_stdout
    return {"status": "execução realizada", "logs": buffer.getvalue()}

@app.get("/testar_whatsapp")
def testar_whatsapp():
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer
    try:
        enviar_leitura_whatsapp.main()
    except Exception as e:
        print("❌ Erro:", e)
    finally:
        sys.stdout = old_stdout
    return JSONResponse(content={"logs": buffer.getvalue()})

# ---------------------------
# Health
# ---------------------------
@app.get("/_health")
def health():
    return {"status": "ok", "versao_atual": get_versao_atual()}

# ---------------------------
# Run (dev)
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
