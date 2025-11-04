from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, os
from models import LIVROS_NOMES
import io
import sys
from fastapi.responses import PlainTextResponse
import enviar_leitura_whatsapp
app = FastAPI()

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
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
        caminho = os.path.join(BASE_DIR, "uploads", file.filename)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "wb") as f:
            f.write(conteudo)
        mensagem = f"Imagem '{file.filename}' enviada com sucesso!"
    except Exception as e:
        mensagem = f"Erro ao processar a imagem: {e}"

    return templates.TemplateResponse("upload.html", {"request": request, "mensagem": mensagem})

# --- Rota para processar OCR ---
@app.get("/processar_ocr")
def processar_ocr():
    uploads_dir = Path("uploads")
    processadas_dir = uploads_dir / "processadas"
    processadas_dir.mkdir(exist_ok=True)

    mensagens = []
    for img_path in uploads_dir.glob("*.*"):
        if (processadas_dir / img_path.name).exists():
            continue  # já processada

        try:
            texto = pytesseract.image_to_string(Image.open(img_path), lang="por")
            
            # salva no JSON de leituras
            enviar_leitura_whatsapp.garantir_estrutura()
            with open(enviar_leitura_whatsapp.LEITURAS_JSON, "r+", encoding="utf-8") as f:
                leituras = json.load(f)
                leituras.append({"data_envio": str(datetime.date.today()), "texto": texto})
                f.seek(0)
                json.dump(leituras, f, ensure_ascii=False, indent=2)
                f.truncate()

            mensagens.append(f"✅ {img_path.name} processada com sucesso!")
            img_path.rename(processadas_dir / img_path.name)
        except Exception as e:
            mensagens.append(f"❌ Erro em {img_path.name}: {e}")

    return {"mensagens": mensagens}


# -------------------------------------------------------
# Inicialização
# -------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

# --- Rota temporária para enviar versículo do dia ---
from fastapi import FastAPI

# Evita criar outro app se já existir
try:
    app
except NameError:
    app = FastAPI()

import enviar_leitura_whatsapp

@app.get("/enviar_versiculo")
def enviar_versiculo():
    print("=== Iniciando envio de versículo do dia ===")
    enviar_leitura_whatsapp.main()
    print("=== Fim do envio ===")
    return {"status": "Execução realizada, verifique os logs para detalhes"}


@app.get("/testar_whatsapp", response_class=PlainTextResponse)
def testar_whatsapp():
    buffer = io.StringIO()
    sys.stdout = buffer
    try:
        enviar_leitura_whatsapp.main()  # apenas chama a função main
    except Exception as e:
        print("❌ Erro:", e)
    finally:
        sys.stdout = sys.__stdout__
    return buffer.getvalue()
