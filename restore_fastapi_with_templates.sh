#!/usr/bin/env bash
set -e

# main.py + templates (sobrescreve)
cat > main.py <<'PY'
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import json, os
from models import LIVROS_NOMES, carregar_biblia

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="mudar_esta_chave_para_producao")

# templates / static
templates = Jinja2Templates(directory="templates")
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

# lista de versões (arquivos .json)
VERSOES = sorted([f.replace(".json","") for f in os.listdir(DATA_DIR) if f.endswith(".json")])

def versao_atual(request: Request):
    return request.session.get("versao", "nvi")

def carregar_biblia_versao(versao):
    path = os.path.join(DATA_DIR, f"{versao}.json")
    return carregar_biblia(path)  # usa a função do seu models.py (que trata utf-8-sig)

@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/livros")

@app.get("/trocar_versao")
def trocar_versao(request: Request, versao: str = "nvi"):
    if versao in VERSOES:
        request.session["versao"] = versao
    return RedirectResponse(url="/livros")

@app.get("/livros", response_class=HTMLResponse)
def livros(request: Request):
    versao = versao_atual(request)
    biblia = carregar_biblia_versao(versao)
    return templates.TemplateResponse("livros.html", {
        "request": request,
        "livros": biblia,
        "versao": versao,
        "versoes": VERSOES,
        "LIVROS_NOMES": LIVROS_NOMES
    })

@app.get("/capitulos/{livro_abrev}", response_class=HTMLResponse)
def capitulos(request: Request, livro_abrev: str):
    versao = versao_atual(request)
    biblia = carregar_biblia_versao(versao)
    livro = next((l for l in biblia if l.get("abbrev") == livro_abrev), None)
    if not livro:
        return HTMLResponse("<h3>Livro não encontrado</h3>", status_code=404)
    total = len(livro.get("chapters", []))
    return templates.TemplateResponse("capitulos.html", {
        "request": request,
        "livro": livro,
        "total": total,
        "versao": versao,
        "versoes": VERSOES,
        "LIVROS_NOMES": LIVROS_NOMES
    })

@app.get("/versiculos/{livro_abrev}/{capitulo}", response_class=HTMLResponse)
def versiculos(request: Request, livro_abrev: str, capitulo: int):
    versao = versao_atual(request)
    biblia = carregar_biblia_versao(versao)
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
        "versao": versao,
        "versoes": VERSOES,
        "LIVROS_NOMES": LIVROS_NOMES
    })

# upload separado (interface e processamento)
@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "texto_extraido": None})

from fastapi import File, UploadFile
from PIL import Image
import pytesseract
import io

@app.post("/upload", response_class=HTMLResponse)
async def upload_process(request: Request, file: UploadFile = File(...)):
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert("RGB")
        texto = pytesseract.image_to_string(img, lang="por")
        # opcional: salvar em leitura/versiculos.json
        os.makedirs("leitura", exist_ok=True)
        import datetime
        caminho_json = "leitura/versiculos.json"
        dados = {}
        if os.path.exists(caminho_json):
            try:
                with open(caminho_json,"r",encoding="utf-8") as f:
                    dados = json.load(f)
            except:
                dados = {}
        dados[datetime.date.today().isoformat()] = texto
        with open(caminho_json,"w",encoding="utf-8") as f:
            json.dump(dados,f,ensure_ascii=False,indent=2)
        return templates.TemplateResponse("upload.html", {"request": request, "texto_extraido": texto})
    except Exception as e:
        return templates.TemplateResponse("upload.html", {"request": request, "texto_extraido": f"Erro: {e}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
PY

# base.html
mkdir -p templates
cat > templates/base.html <<'HT'
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Bíblia</title>
  <link rel="stylesheet" href="/static/bootstrap/css/bootstrap.min.css">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-light bg-light mb-3">
  <div class="container-fluid">
    <a class="navbar-brand" href="/livros">📖 Bíblia</a>
    <div class="d-flex">
      <a class="btn btn-outline-secondary me-2" href="/upload">Enviar Cronograma</a>
      <form class="d-flex" action="/trocar_versao" method="get">
        <select class="form-select form-select-sm me-2" name="versao" onchange="this.form.submit()">
          {% for v in versoes %}
            <option value="{{ v }}" {% if v==versao %}selected{% endif %}>{{ v.upper() }}</option>
          {% endfor %}
        </select>
      </form>
    </div>
  </div>
</nav>
<div class="container">
  {% block content %}{% endblock %}
</div>
<script src="/static/bootstrap/js/bootstrap.bundle.min.js"></script>
</body>
</html>
HT

# livros.html (usa estrutura idêntica ao Flask: list of book dicts)
cat > templates/livros.html <<'HT'
{% extends "base.html" %}
{% block content %}
<h1>Escolha um livro</h1>
<div class="row">
  {% for livro in livros %}
    <div class="col-6 col-md-4 col-lg-3 mb-2">
      <a class="btn btn-primary w-100 text-start" href="/capitulos/{{ livro.abbrev }}">
        {{ LIVROS_NOMES.get(livro.abbrev, livro.name) }}
      </a>
    </div>
  {% endfor %}
</div>
{% endblock %}
HT

# capitulos.html
cat > templates/capitulos.html <<'HT'
{% extends "base.html" %}
{% block content %}
<h2>{{ LIVROS_NOMES.get(livro.abbrev, livro.name) }}</h2>
<p>Selecione um capítulo:</p>
<div class="row row-cols-1 row-cols-md-6 g-3">
  {% for i in range(1, total+1) %}
    <div class="col">
      <a href="/versiculos/{{ livro.abbrev }}/{{ i }}" class="btn btn-success w-100">Capítulo {{ i }}</a>
    </div>
  {% endfor %}
</div>
<a href="/livros" class="btn btn-link mt-3">⬅ Voltar</a>
{% endblock %}
HT

# versiculos.html
cat > templates/versiculos.html <<'HT'
{% extends "base.html" %}
{% block content %}
<h2>{{ LIVROS_NOMES.get(livro.abbrev, livro.name) }} - Capítulo {{ capitulo }}</h2>
<div class="mt-3">
  {% for v in versiculos %}
    <p><strong>{{ loop.index }}.</strong> {{ v }}</p>
  {% endfor %}
</div>
<a href="/capitulos/{{ livro.abbrev }}" class="btn btn-link mt-3">⬅ Voltar</a>
{% endblock %}
HT

# upload.html
cat > templates/upload.html <<'HT'
{% extends "base.html" %}
{% block content %}
<h2>Enviar imagem do cronograma</h2>
<p>Envie uma imagem com as leituras (ex: "01/11 - João 1"). O sistema fará OCR e salvará a leitura.</p>

<div class="card mb-3">
  <div class="card-body">
    <form action="/upload" method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <input class="form-control" type="file" name="file" accept="image/*" required>
      </div>
      <button class="btn btn-primary" type="submit">Enviar imagem</button>
    </form>
  </div>
</div>

{% if texto_extraido %}
<div class="card">
  <div class="card-header">Texto extraído</div>
  <div class="card-body"><pre style="white-space: pre-wrap;">{{ texto_extraido }}</pre></div>
</div>
{% endif %}

<a href="/livros" class="btn btn-link mt-3">⬅ Voltar</a>
{% endblock %}
HT

# make script executable (optional)
chmod +x restore_fastapi_with_templates.sh

echo "Arquivos escritos: main.py e templates/* — execute 'git add . && git commit -m \"restaura fastapi/templates\" && git push' para atualizar o repositório."
