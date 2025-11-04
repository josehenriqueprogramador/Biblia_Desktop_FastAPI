from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, os, io, sys
import enviar_leitura_whatsapp
from models import LIVROS_NOMES

app = FastAPI()

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
LEITURAS_DIR = os.path.join(BASE_DIR, "leituras")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(LEITURAS_DIR, exist_ok=True)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# -------------------------------------------------------
# Funções auxiliares
# -------------------------------------------------------
def listar_versoes():
    return sorted([f.replace(".json","") for f in os.listdir(DATA_DIR) if f.endswith(".json")])

def carregar_biblia(versao):
    caminho = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(caminho):
        return []
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
# Rotas principais
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

@app.get("/versiculos/{livro_abrev}/{capitulo}", response_class=HTMLResponse)
async def versiculos(request: Request, livro_abrev: str, capitulo: int):
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

# -------------------------------------------------------
# Upload de imagem do cronograma (OCR)
# -------------------------------------------------------
@app.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
async def upload_cronograma(request: Request, file: UploadFile = File(...)):
    try:
        conteudo = await file.read()
        caminho = os.path.join(UPLOADS_DIR, file.filename)
        with open(caminho, "wb") as f:
            f.write(conteudo)
        mensagem = f"Imagem '{file.filename}' enviada com sucesso!"
        # Aqui você pode chamar sua função de OCR e salvar no leituras.json
        # Exemplo: enviar_leitura_whatsapp.processar_imagem(caminho)
    except Exception as e:
        mensagem = f"Erro ao processar a imagem: {e}"
    return templates.TemplateResponse("upload.html", {"request": request, "mensagem": mensagem})

# -------------------------------------------------------
# Rotas para envio do versículo do dia
# -------------------------------------------------------
@app.get("/enviar_versiculo")
def enviar_versiculo():
    buffer = io.StringIO()
    sys.stdout = buffer
    try:
        enviar_leitura_whatsapp.main()
    except Exception as e:
        print("❌ Erro:", e)
    finally:
        sys.stdout = sys.__stdout__
    return {"status": "Execução realizada, verifique os logs para detalhes"}

@app.get("/testar_whatsapp", response_class=PlainTextResponse)
def testar_whatsapp():
    buffer = io.StringIO()
    sys.stdout = buffer
    try:
        enviar_leitura_whatsapp.main()
    except Exception as e:
        print("❌ Erro:", e)
    finally:
        sys.stdout = sys.__stdout__
    return buffer.getvalue()

# -------------------------------------------------------
# Inicialização
# -------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
