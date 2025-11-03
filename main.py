from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, json
from PIL import Image
import pytesseract
from models import LIVROS_NOMES  # seu models.py existente

app = FastAPI()

# Configura templates e estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

# Carrega lista de versões disponíveis (apenas nomes dos arquivos .json)
VERSOES = sorted([f.replace(".json","") for f in os.listdir(DATA_DIR) if f.endswith(".json")])

# Função segura para abrir JSONs com BOM tratado
def carregar_json_com_bom(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

# Função que carrega a bíblia da versão padrão (nvi) usando utf-8-sig
VERSAO_PADRAO = "nvi"
def obter_biblia(versao=VERSAO_PADRAO):
    path = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(path):
        return []
    return carregar_json_com_bom(path)

# Rota raiz: lista todos os livros (usando JSON da versão padrão)
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    biblia = obter_biblia()
    return templates.TemplateResponse("livros.html", {
        "request": request,
        "biblia": biblia,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": VERSOES,
        "versao": VERSAO_PADRAO
    })

# Lista capítulos de um livro (recebe abreviação)
@app.get("/capitulos/{livro_abrev}", response_class=HTMLResponse)
async def capitulos(request: Request, livro_abrev: str, versao: str = VERSAO_PADRAO):
    biblia = obter_biblia(versao)
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        return HTMLResponse("<h3>Livro não encontrado</h3>", status_code=404)
    total = len(livro.get("chapters", []))
    return templates.TemplateResponse("capitulos.html", {
        "request": request,
        "livro": livro,
        "total": total,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": VERSOES,
        "versao": versao
    })

# Exibe versículos de um capítulo
@app.get("/versiculos/{livro_abrev}/{capitulo}", response_class=HTMLResponse)
async def versiculos(request: Request, livro_abrev: str, capitulo: int, versao: str = VERSAO_PADRAO):
    biblia = obter_biblia(versao)
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        return HTMLResponse("<h3>Livro não encontrado</h3>", status_code=404)
    chapters = livro.get("chapters", [])
    if capitulo < 1 or capitulo > len(chapters):
        return HTMLResponse("<h3>Capítulo não encontrado</h3>", status_code=404)
    versiculos = chapters[capitulo - 1]
    return templates.TemplateResponse("versiculos.html", {
        "request": request,
        "livro": livro,
        "capitulo": capitulo,
        "versiculos": versiculos,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": VERSOES,
        "versao": versao
    })

# Página de upload (form)
@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "texto": None})

# Processa imagem enviada (campo name="imagem" no form)
@app.post("/upload", response_class=HTMLResponse)
async def processar_imagem(request: Request, imagem: UploadFile = File(...)):
    if not imagem:
        return templates.TemplateResponse("upload.html", {"request": request, "texto": "Nenhuma imagem enviada."})
    try:
        # lê bytes da imagem (UploadFile)
        conteudo = await imagem.read()
        img = Image.open(io.BytesIO(conteudo)) if 'io' in globals() else Image.open(imagem.file)
        texto_extraido = pytesseract.image_to_string(img, lang="por")
        return templates.TemplateResponse("upload.html", {"request": request, "texto": texto_extraido})
    except Exception as e:
        return templates.TemplateResponse("upload.html", {"request": request, "texto": f"Erro: {str(e)}"})

# rota de teste para verificar carregamento com utf-8-sig
@app.get("/_debug_load/{versao}", response_class=HTMLResponse)
async def debug_load(request: Request, versao: str):
    path = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(path):
        return HTMLResponse(f"<pre>Arquivo {path} não encontrado</pre>", status_code=404)
    try:
        data = carregar_json_com_bom(path)
        return HTMLResponse(f"<pre>OK — {versao}: {len(data)} livros carregados</pre>")
    except Exception as e:
        return HTMLResponse(f"<pre>Erro ao carregar {versao}: {e}</pre>", status_code=500)

if __name__ == "__main__":
    import uvicorn, io
    uvicorn.run(app, host="0.0.0.0", port=5000)
