"""
main.py - FastAPI app alinhado com models.py (objetos Livro/Capitulo/Versiculo).

Rotas:
  GET  /             -> redireciona para /livros
  GET  /livros       -> lista objetos Livro (usa carregar_biblia)
  GET  /capitulos/{livro_abrev}  -> mostra capítulos do Livro
  GET  /versiculos/{livro_abrev}/{capitulo} -> mostra versículos do capítulo (usa Capitulo.versiculos -> Versiculo.texto)
  GET  /upload       -> página de upload (template)
  POST /upload       -> recebe imagem, OCR, persiste em leitura/versiculos.json e retorna template com texto extraído

Requisitos:
  - models.py deve exportar LIVROS_NOMES e carregar_biblia(caminho) que retorna lista de objetos Livro conforme seu arquivo.
  - templates: livros.html, capitulos.html, versiculos.html, upload.html (devem usar atributos .abrev, .nome, .capitulos, .versiculos, Versiculo.texto)
"""

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, json, io, datetime
from models import LIVROS_NOMES, carregar_biblia
from PIL import Image
import pytesseract

# ---------- Config ----------
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
LEITURA_DIR = os.path.join(BASE_DIR, "leitura")
LEITURA_FILE = os.path.join(LEITURA_DIR, "versiculos.json")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(LEITURA_DIR, exist_ok=True)

app = FastAPI()
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

DEFAULT_VERSAO = "nvi"

# ---------- Helpers ----------
def listar_versoes():
    """Retorna nomes de arquivos JSON em data/ sem extensão."""
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted([f[:-5] for f in os.listdir(DATA_DIR) if f.endswith(".json")])

def carregar_objetos_biblia(versao: str = DEFAULT_VERSAO):
    """Usa carregar_biblia do models.py e retorna lista de objetos Livro.
       Se falhar, tenta carregar o JSON cru (fallback)."""
    caminho = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(caminho):
        return []
    try:
        livros = carregar_biblia(caminho)
        return livros
    except Exception:
        with open(caminho, "r", encoding="utf-8-sig") as f:
            return json.load(f)

def persistir_leitura(data_iso: str, texto: str):
    """Salva/atualiza leitura/versiculos.json como dicionário data_iso -> texto."""
    dados = {}
    if os.path.exists(LEITURA_FILE):
        try:
            with open(LEITURA_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception:
            dados = {}
    dados[data_iso] = texto
    with open(LEITURA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def ler_leitura_por_data(data_iso: str):
    if not os.path.exists(LEITURA_FILE):
        return None
    try:
        with open(LEITURA_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados.get(data_iso)
    except Exception:
        return None

# ---------- Rotas ----------
@app.get("/", response_class=HTMLResponse)
async def raiz():
    return RedirectResponse(url="/livros")

@app.get("/livros", response_class=HTMLResponse)
async def rota_livros(request: Request, versao: str = DEFAULT_VERSAO):
    """Lista objetos Livro — passa objetos para templates (usa livro.abrev e livro.nome)."""
    versoes = listar_versoes()
    livros = carregar_objetos_biblia(versao)
    # livros: lista de objetos Livro (com .abrev e .nome e .capitulos)
    return templates.TemplateResponse("livros.html", {
        "request": request,
        "livros": livros,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": versoes,
        "versao": versao
    })

@app.get("/capitulos/{livro_abrev}", response_class=HTMLResponse)
async def rota_capitulos(request: Request, livro_abrev: str, versao: str = DEFAULT_VERSAO):
    """Mostra capítulos usando livro.get_capitulo(n) e livro.capitulos (lista)."""
    livros = carregar_objetos_biblia(versao)
    livro = next((l for l in livros if getattr(l, "abrev", None) == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    total = len(getattr(livro, "capitulos", []))
    return templates.TemplateResponse("capitulos.html", {
        "request": request,
        "livro": livro,
        "total": total,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": listar_versoes(),
        "versao": versao
    })

@app.get("/versiculos/{livro_abrev}/{capitulo}", response_class=HTMLResponse)
async def rota_versiculos(request: Request, livro_abrev: str, capitulo: int, versao: str = DEFAULT_VERSAO):
    """Renderiza versículos de um capítulo. Usa livro.get_capitulo(capitulo) -> Capitulo obj com .versiculos (list of Versiculo)."""
    livros = carregar_objetos_biblia(versao)
    livro = next((l for l in livros if getattr(l, "abrev", None) == livro_abrev), None)
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    cap = livro.get_capitulo(capitulo)
    if not cap:
        return HTMLResponse("Capítulo não encontrado", status_code=404)
    # cap.versiculos é lista de Versiculo objetos; cada Versiculo tem .numero e .texto
    return templates.TemplateResponse("versiculos.html", {
        "request": request,
        "livro": livro,
        "capitulo": cap.numero,
        "versiculos": cap.versiculos,
        "LIVROS_NOMES": LIVROS_NOMES,
        "versoes": listar_versoes(),
        "versao": versao
    })

# ---- Upload OCR (interface simples) ----
@app.get("/upload", response_class=HTMLResponse)
async def upload_get(request: Request, versao: str = DEFAULT_VERSAO):
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "mensagem": None,
        "texto_extraido": None,
        "versoes": listar_versoes(),
        "versao": versao
    })

@app.post("/upload", response_class=HTMLResponse)
async def upload_post(request: Request, file: UploadFile = File(...), versao: str = DEFAULT_VERSAO):
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert("RGB")
        texto = pytesseract.image_to_string(img, lang="por")
        # persiste leitura com data atual ISO (YYYY-MM-DD)
        hoje = datetime.date.today().isoformat()
        persistir_leitura(hoje, texto.strip())
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "mensagem": "Imagem enviada e texto persistido em leitura/versiculos.json",
            "texto_extraido": texto,
            "versoes": listar_versoes(),
            "versao": versao
        })
    except Exception as e:
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "mensagem": f"Erro ao processar imagem: {e}",
            "texto_extraido": None,
            "versoes": listar_versoes(),
            "versao": versao
        })

# ---- rota para ver leitura de hoje (JSON) ----
@app.get("/versiculo-hoje")
async def versiculo_hoje(versao: str = DEFAULT_VERSAO):
    hoje = datetime.date.today().isoformat()
    texto = ler_leitura_por_data(hoje)
    if not texto:
        return {"data": hoje, "texto": None, "info": "Nenhuma leitura encontrada"}
    return {"data": hoje, "texto": texto}

# ---------- Execução local ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
