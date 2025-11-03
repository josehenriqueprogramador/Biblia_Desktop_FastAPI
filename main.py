from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
import pytesseract
import requests
import json
import datetime
import io
import os

# ----------------- Configurações Z-API -----------------
ZAPI_INSTANCE = "3E9A42A3E2CED133DB7B122EE267B15F"
ZAPI_TOKEN = "B515A074755027E95E2DD22E"
NUMERO_DESTINO = "5521920127396"
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"

# ----------------- Diretórios -----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
static_dir = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
LEITURAS_DIR = os.path.join(BASE_DIR, "leituras")
VERSICULOS_FILE = os.path.join(LEITURAS_DIR, "versiculos.json")
NVI_FILE = os.path.join(DATA_DIR, "nvi.json")

os.makedirs(LEITURAS_DIR, exist_ok=True)

# ----------------- Inicializar app -----------------
app = FastAPI()
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ----------------- Funções -----------------
def enviar_whatsapp(mensagem: str):
    payload = {"phone": NUMERO_DESTINO, "message": mensagem}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(ZAPI_URL, json=payload, headers=headers)
        if response.status_code == 200:
            print("✅ Mensagem enviada com sucesso!")
        else:
            print("❌ Erro ao enviar:", response.status_code, response.text)
    except Exception as e:
        print("⚠️ Falha na conexão com Z-API:", e)

def carregar_versiculos():
    if os.path.exists(VERSICULOS_FILE):
        with open(VERSICULOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_versiculos(dados):
    with open(VERSICULOS_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

def parse_versiculos(texto_ocr):
    # Ajusta os versículos para formato correto usando NVI
    if not os.path.exists(NVI_FILE):
        print("❌ NVI.json não encontrado")
        return texto_ocr
    with open(NVI_FILE, "r", encoding="utf-8") as f:
        biblia = json.load(f)

    linhas = texto_ocr.splitlines()
    resultado = []

    for linha in linhas:
        linha = linha.strip()
        if not linha or linha.startswith("DIA"):
            continue
        refs = linha.replace("+", ",").replace("«", ",").split(",")
        for ref in refs:
            ref = ref.strip()
            if " " not in ref:
                continue
            try:
                livro, cap_vers = ref.split(" ", 1)
                if ":" in cap_vers:
                    cap, vers = cap_vers.split(":")
                    if "-" in vers:
                        inicio, fim = map(int, vers.split("-"))
                        for i in range(inicio, fim+1):
                            texto = biblia.get(livro, {}).get(cap, {}).get(str(i), "")
                            if texto:
                                resultado.append(f"{livro} {cap}:{i} — {texto}")
                    else:
                        texto = biblia.get(livro, {}).get(cap, {}).get(vers, "")
                        if texto:
                            resultado.append(f"{livro} {cap}:{vers} — {texto}")
                else:
                    texto = biblia.get(livro, {}).get(cap_vers, "")
                    if texto:
                        resultado.append(f"{livro} {cap_vers} — {texto}")
            except Exception:
                continue
    return "\n".join(resultado)

def leitura_do_dia():
    hoje = datetime.date.today().isoformat()
    versiculos = carregar_versiculos()
    leitura_hoje = next((v for v in versiculos if v["data_envio"] == hoje), None)
    if leitura_hoje:
        return parse_versiculos(leitura_hoje["texto"])
    return None

# ----------------- Rotas -----------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/versiculo-hoje")
async def versiculo_hoje():
    texto = leitura_do_dia()
    if texto:
        return {"data": datetime.date.today().isoformat(), "texto": texto}
    return {"data": datetime.date.today().isoformat(), "texto": None, "info": "Nenhuma leitura encontrada"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        texto_extraido = pytesseract.image_to_string(image, lang="por")
        novo_registro = {"data_envio": datetime.date.today().isoformat(), "texto": texto_extraido.strip()}

        versiculos = carregar_versiculos()
        versiculos.append(novo_registro)
        salvar_versiculos(versiculos)

        texto_final = parse_versiculos(texto_extraido)
        enviar_whatsapp(texto_final if texto_final else "⚠️ Nenhuma leitura encontrada para hoje.")
        return JSONResponse({"mensagem": "Imagem enviada e leitura processada!", "texto_extraido": texto_extraido.strip()})
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)

# ----------------- Execução local -----------------
if __name__ == "__main__":
    import uvicorn
    texto_hoje = leitura_do_dia()
    enviar_whatsapp(texto_hoje if texto_hoje else "⚠️ Nenhuma leitura encontrada para hoje.")
    uvicorn.run(app, host="0.0.0.0", port=5000)
