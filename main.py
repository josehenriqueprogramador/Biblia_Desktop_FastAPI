from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse
import json
import os
import io
import sys
import tempfile
import enviar_leitura_whatsapp
from models import LIVROS_NOMES
from typing import List

# ---------------------------
# Config
# ---------------------------
app = FastAPI()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
LEITURAS_DIR = os.path.join(BASE_DIR, "leituras")
VERSAO_FILE = os.path.join(DATA_DIR, "versao_atual.txt")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(LEITURAS_DIR, exist_ok=True)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# ---------------------------
# CORS - configure via ENV in produção
# ---------------------------
# Em produção, defina a variável de ambiente ALLOWED_ORIGINS como JSON:
#   export ALLOWED_ORIGINS='["https://meusite.com"]'
try:
    allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
    if allowed_origins_env:
        import ast
        ALLOWED_ORIGINS = ast.literal_eval(allowed_origins_env)
    else:
        ALLOWED_ORIGINS = ["*"]  # dev default; **troque em produção**
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
# Helpers: versões / arquivos
# ---------------------------
def listar_versoes() -> List[str]:
    """Lista as versões válidas (arquivos .json em DATA_DIR)."""
    try:
        return sorted(
            f.replace(".json","")
            for f in os.listdir(DATA_DIR)
            if f.endswith(".json") and not f.startswith("_")
        )
    except FileNotFoundError:
        return []

def carregar_biblia(versao: str):
    """Retorna a estrutura JSON da versão ou [] se não existir."""
    caminho = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def get_versao_atual(default: str = "nvi") -> str:
    """Lê a versão atual do arquivo (persistente)."""
    try:
        if os.path.exists(VERSAO_FILE):
            with open(VERSAO_FILE, "r", encoding="utf-8") as f:
                v = f.read().strip()
                return v or default
    except Exception:
        pass
    return default

def set_versao_atual(valor: str) -> None:
    """Escreve a versão atual de forma atômica para evitar arquivos corrompidos."""
    os.makedirs(os.path.dirname(VERSAO_FILE), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(VERSAO_FILE))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(valor)
        os.replace(tmp_path, VERSAO_FILE)
    except Exception:
        # cleanup se algo deu errado
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        raise

# ---------------------------
# Segurança: sanitizar referer
# ---------------------------
def safe_redirect_target(request: Request, target: str) -> str:
    """
    Retorna target se for interno (mesmo host) ou caminho relativo.
    Caso contrário retorna URL para /livros.
    """
    if not target:
        return request.url_for("livros")
    parsed = urlparse(target)
    # se não houver netloc => é caminho relativo -> permitir
    if not parsed.netloc:
        return target
    # se netloc existir, permitir somente se for mesmo host
    request_host = request.url.hostname
    if parsed.hostname == request_host:
        return target
    # caso contrário, bloqueia e redireciona para /livros
    return request.url_for("livros")

# ---------------------------
# Rotas
# ---------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return RedirectResponse(url=request.url_for("livros"))

@app.get("/livros", response_class=HTMLResponse)
async def livros(request: Request):
    versao_atual = get_versao_atual()
    biblia = carregar_biblia(versao_atual)
    return templates.TemplateResponse("livros.html", {
        "request": request,
        "livros": biblia,
        "versao": versao_atual,
        "versoes": listar_versoes(),
        "LIVROS_NOMES": LIVROS_NOMES
    })

# Trocar versão: preferir POST para mudança de estado, mas manter GET por compatibilidade.
@app.post("/trocar_versao", response_class=HTMLResponse)
async def trocar_versao_post(request: Request, versao: str = Form(...), voltar_para: str = Form(None)):
    """
    POST recomendado: altera a versão e volta para 'voltar_para' (se válido) ou /livros.
    'voltar_para' pode ser um caminho relativo ou full URL local.
    """
    versoes = listar_versoes()
    if versao not in versoes:
        # Fail hard: cliente tentou setar versão inválida
        raise HTTPException(status_code=400, detail="Versão inválida.")
    set_versao_atual(versao)
    target = safe_redirect_target(request, voltar_para)
    return RedirectResponse(url=target)

@app.get("/trocar_versao", response_class=HTMLResponse)
async def trocar_versao_get(request: Request, versao: str = "nvi"):
    """
    GET para compatibilidade: altera a versão somente se for válida, e volta para Referer (só se seguro),
    caso contrário volta para /livros.
    Nota: em produção prefira usar POST.
    """
    if versao in listar_versoes():
        set_versao_atual(versao)
    # pegar referer de forma segura
    referer = request.headers.get("referer")
    target = safe_redirect_target(request, referer)
    return RedirectResponse(url=target)

@app.get("/capitulos/{livro_abrev}", response_class=HTMLResponse)
async def capitulos(request: Request, livro_abrev: str):
    versao_atual = get_versao_atual()
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

@app.get("/versiculos/{livro_abrev}/{capitulo}", response_class=HTMLResponse)
async def versiculos(request: Request, livro_abrev: str, capitulo: int):
    versao_atual = get_versao_atual()
    biblia = carregar_biblia(versao_atual)
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
        "versao": versao_atual,
        "versoes": listar_versoes(),
        "LIVROS_NOMES": LIVROS_NOMES
    })

# Upload
@app.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
async def upload_cronograma(request: Request, file: UploadFile = File(...)):
    try:
        conteudo = await file.read()
        # sanitize filename (remova caminhos etc.)
        filename = os.path.basename(file.filename)
        caminho = os.path.join(UPLOADS_DIR, filename)
        with open(caminho, "wb") as f:
            f.write(conteudo)
        mensagem = f"Imagem '{filename}' enviada com sucesso!"
        # Chamar OCR/processing se necessário, ex:
        # enviar_leitura_whatsapp.processar_imagem(caminho)
    except Exception as e:
        mensagem = f"Erro ao processar a imagem: {e}"
    return templates.TemplateResponse("upload.html", {"request": request, "mensagem": mensagem})

# Rotas WhatsApp / execução
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
    return {"status": "Execução realizada, verifique os logs para detalhes"}

@app.get("/testar_whatsapp", response_class=PlainTextResponse)
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
    return buffer.getvalue()

# Health / debug
@app.get("/_health", response_class=JSONResponse)
def health():
    return {"status": "ok", "versao_atual": get_versao_atual()}

# ---------------------------
# Run (dev)
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

