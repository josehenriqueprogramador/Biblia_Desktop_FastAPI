from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, json, io, datetime
from models import LIVROS_NOMES, carregar_biblia
from PIL import Image
import pytesseract

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
LEITURA_DIR = os.path.join(BASE_DIR, "leitura")
os.makedirs(LEITURA_DIR, exist_ok=True)

app = FastAPI()
if os.path.isdir(os.path.join(BASE_DIR, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

DEFAULT_VERSAO = "nvi"

def listar_versoes():
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted([f[:-5] for f in os.listdir(DATA_DIR) if f.endswith(".json")])

def carregar_objetos_biblia(versao=DEFAULT_VERSAO):
    caminho = os.path.join(DATA_DIR, f"{versao}.json")
    if not os.path.exists(caminho):
        return []
    try:
        return carregar_biblia(caminho)  # retorna lista de objetos Livro
    except Exception:
        with open(caminho, "r", encoding="utf-8-sig") as f:
            return json.load(f)  # fallback: lista de dicts

@app.get("/", response_class=HTMLResponse)
async def raiz():
    return RedirectResponse(url="/livros")

@app.get("/livros", response_class=HTMLResponse)
async def rota_livros(request: Request, versao: str = DEFAULT_VERSAO):
    """
    Garante sempre passar para o template uma lista de dicts:
      livros = [{"abrev": "Gn", "nome": "Gênesis"}, ...]
    Nome é preferencialmente obtido de LIVROS_NOMES, senão do objeto/dict.
    """
    versoes = listar_versoes()
    raw = carregar_objetos_biblia(versao)
    livros_out = []
    for item in raw:
        # suporta objeto (com .abrev, .nome) ou dict (com 'abbrev'/'name')
        if hasattr(item, "abrev"):
            abrev = getattr(item, "abrev", None)
            nome_obj = getattr(item, "nome", None)
        else:
            abrev = item.get("abbrev") or item.get("abrev") or item.get("ab")
            nome_obj = item.get("name") or item.get("nome")
        # resolve nome usando dicionário primeiro (LIVROS_NOMES), fallback para nome do objeto/dict, fallback para abreviação
        nome = LIVROS_NOMES.get(abrev) if abrev else None
        if not nome:
            nome = nome_obj or abrev or "(sem nome)"
        livros_out.append({"abrev": abrev, "nome": nome})
    return templates.TemplateResponse("livros.html", {
        "request": request,
        "livros": livros_out,
        "versoes": versoes,
        "versao": versao
    })

@app.get("/capitulos/{livro_abrev}", response_class=HTMLResponse)
async def rota_capitulos(request: Request, livro_abrev: str, versao: str = DEFAULT_VERSAO):
    livros = carregar_objetos_biblia(versao)
    # procura objeto/dict por abreviação
    livro = None
    for item in livros:
        if hasattr(item, "abrev") and getattr(item, "abrev", None) == livro_abrev:
            livro = item; break
        if isinstance(item, dict) and item.get("abbrev") == livro_abrev:
            livro = item; break
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    # determina total de capítulos de forma robusta
    if hasattr(livro, "capitulos"):
        total = len(getattr(livro, "capitulos", []))
        nome = getattr(livro, "nome", LIVROS_NOMES.get(livro_abrev, livro_abrev))
    else:
        chapters = livro.get("chapters", [])
        total = len(chapters)
        nome = LIVROS_NOMES.get(livro_abrev) or livro.get("name") or livro_abrev
    return templates.TemplateResponse("capitulos.html", {
        "request": request,
        "livro_abrev": livro_abrev,
        "nome": nome,
        "total": total,
        "versoes": listar_versoes(),
        "versao": versao
    })

@app.get("/versiculos/{livro_abrev}/{capitulo}", response_class=HTMLResponse)
async def rota_versiculos(request: Request, livro_abrev: str, capitulo: int, versao: str = DEFAULT_VERSAO):
    livros = carregar_objetos_biblia(versao)
    livro = None
    for item in livros:
        if hasattr(item, "abrev") and getattr(item, "abrev", None) == livro_abrev:
            livro = item; break
        if isinstance(item, dict) and item.get("abbrev") == livro_abrev:
            livro = item; break
    if not livro:
        return HTMLResponse("Livro não encontrado", status_code=404)
    # extrai versículos de forma compatível com objeto ou dict
    versiculos_list = []
    if hasattr(livro, "get_capitulo"):
        cap = livro.get_capitulo(capitulo)
        if not cap:
            return HTMLResponse("Capítulo não encontrado", status_code=404)
        # cap.versiculos é lista de Versiculo objs
        for v in getattr(cap, "versiculos", []):
            texto = getattr(v, "texto", None) or str(v)
            numero = getattr(v, "numero", None)
            versiculos_list.append({"numero": numero, "texto": texto})
        nome = getattr(livro, "nome", LIVROS_NOMES.get(livro_abrev, livro_abrev))
    else:
        chapters = livro.get("chapters", [])
        if capitulo < 1 or capitulo > len(chapters):
            return HTMLResponse("Capítulo não encontrado", status_code=404)
        for i, t in enumerate(chapters[capitulo-1], start=1):
            versiculos_list.append({"numero": i, "texto": t})
        nome = LIVROS_NOMES.get(livro_abrev) or livro.get("name") or livro_abrev
    return templates.TemplateResponse("versiculos.html", {
        "request": request,
        "livro_abrev": livro_abrev,
        "nome": nome,
        "capitulo": capitulo,
        "versiculos": versiculos_list,
        "versoes": listar_versoes(),
        "versao": versao
    })

# Upload OCR (preserva comportamento anterior)
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
        # persiste simples por data
        path = os.path.join(LEITURA_DIR, "versiculos.json")
        dados = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    dados = json.load(f)
            except Exception:
                dados = {}
        dados[datetime.date.today().isoformat()] = texto.strip()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "mensagem": "Imagem processada e salva.",
            "texto_extraido": texto,
            "versoes": listar_versoes(),
            "versao": versao
        })
    except Exception as e:
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "mensagem": f"Erro: {e}",
            "texto_extraido": None,
            "versoes": listar_versoes(),
            "versao": versao
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
