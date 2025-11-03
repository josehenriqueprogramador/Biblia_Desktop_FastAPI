from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pytesseract, json, os, datetime
from PIL import Image

app = FastAPI()

# Monta pastas estáticas e templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Caminhos
DATA_DIR = "data"
LEITURA_JSON = "leitura/versiculos.json"

os.makedirs("leitura", exist_ok=True)

# Página inicial (66 livros)
@app.get("/", response_class=HTMLResponse)
def livros(request: Request):
    try:
        arquivos = [f.replace(".json", "") for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    except Exception as e:
        arquivos = []
    return templates.TemplateResponse("livros.html", {"request": request, "arquivos": arquivos})

# Página de upload de cronograma
@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

# Processar imagem enviada (OCR)
@app.post("/upload", response_class=HTMLResponse)
async def upload_imagem(request: Request, arquivo: UploadFile = File(...)):
    try:
        conteudo = await arquivo.read()
        caminho = f"leitura/{arquivo.filename}"
        with open(caminho, "wb") as f:
            f.write(conteudo)

        img = Image.open(caminho)
        texto_extraido = pytesseract.image_to_string(img, lang="por")

        # Salvar texto OCR no JSON
        hoje = datetime.date.today().isoformat()
        dados = {}
        if os.path.exists(LEITURA_JSON):
            with open(LEITURA_JSON, "r", encoding="utf-8") as f:
                try:
                    dados = json.load(f)
                except:
                    dados = {}

        dados[hoje] = texto_extraido
        with open(LEITURA_JSON, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)

        return templates.TemplateResponse("upload.html", {"request": request, "mensagem": "Imagem lida e salva!", "texto": texto_extraido})
    except Exception as e:
        return JSONResponse({"erro": f"Falha ao processar: {str(e)}"})

# Rota do versículo do dia
@app.get("/versiculo-hoje", response_class=JSONResponse)
def versiculo_hoje():
    hoje = datetime.date.today().isoformat()
    if not os.path.exists(LEITURA_JSON):
        return {"data": hoje, "texto": None, "info": "Nenhuma leitura encontrada"}

    with open(LEITURA_JSON, "r", encoding="utf-8") as f:
        dados = json.load(f)

    if hoje not in dados:
        return {"data": hoje, "texto": None, "info": "Nenhuma leitura encontrada"}

    return {"data": hoje, "texto": dados[hoje]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
