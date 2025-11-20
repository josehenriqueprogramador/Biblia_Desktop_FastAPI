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
# VERSÃO ORIGINAL (ANTES) — NÃO REDIRECIONAVA PARA A MESMA PÁGINA
# -------------------------------------------------------
# VERSAO_ATUAL = "nvi"
# @app.get("/trocar_versao")
# async def trocar_versao_antigo(versao: str = Query("nvi")):
#     global VERSAO_ATUAL
#     VERSAO_ATUAL = versao
#     return RedirectResponse("/livros")
#
# OBS: Esse código SEMPRE mandava para /livros.
# -------------------------------------------------------


# -------------------------------------------------------
# VERSÃO NOVA (DEPOIS) — AGORA VOLTA PARA A MESMA PÁGINA
# -------------------------------------------------------

VERSAO_ATUAL = "nvi"

def versao_atual():
    return VERSAO_ATUAL


@app.get("/trocar_versao")
async def trocar_versao(request: Request, versao: str = Query("nvi")):
    """
    Agora a versão é trocada e o usuário volta para a MESMA página
    usando o header Referer.
    """

    global VERSAO_ATUAL
    versoes_disponiveis = listar_versoes()

    if versao not in versoes_disponiveis:
        raise HTTPException(status_code=400, detail="Versão inválida.")

    # Troca a versão
    VERSAO_ATUAL = versao

    # Pega a página anterior
    referer = request.headers.get("referer")

    # Se não tiver referer, volta para /livros
    voltar_para = referer or "/livros"

    return RedirectResponse(voltar_para)

# -------------------------------------------------------
# Continua o resto do seu código normalmente...
# -------------------------------------------------------

