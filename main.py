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

# ---------------- TENTATIVA SEGURA DE IMPORTAR APSCHEDULER ----------------
try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ModuleNotFoundError:
    BackgroundScheduler = None
    print("⚠️ APScheduler não instalado — tarefas automáticas desativadas.")

# ---------------- CONFIGURAÇÕES ----------------
ZAPI_INSTANCE = "3E9A42A3E2CED133DB7B122EE267B15F"
ZAPI_TOKEN = "B515A074755027E95E2DD22E"
NUMERO_DESTINO = "5521920127396"
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
static_dir = os.path.join(BASE_DIR, "static")
LEITURAS_DIR = os.path.join(BASE_DIR, "leituras")
JSON_FILE = os.path.join(LEITURAS_DIR, "versiculos.json")

# ---------------- GARANTIR PASTA E JSON ----------------
os.makedirs(LEITURAS_DIR, exist_ok=True)
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)

# ---------------- INICIAR APP ----------------
app = FastAPI()
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ---------------- FUNÇÕES ----------------
def enviar_whatsapp(mensagem: str):
    payload = {"phone": NUMERO_DESTINO, "message": mensagem}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(ZAPI_URL, json=payload, headers=headers)
        if response.status_code == 200:
            print("✅ Mensagem enviada com sucesso via WhatsApp!")
        else:
            print("❌ Erro ao enviar:", response.status_code, response.text)
    except Exception as e:
        print("⚠️ Falha na conexão com Z-API:", e)

def salvar_leitura(texto: str):
    hoje = datetime.date.today().isoformat()
    novo_registro = {"data_envio": hoje, "texto": texto.strip()}
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        dados = []
    dados.append(novo_registro)
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)
    return novo_registro

def get_versiculo_hoje():
    hoje = datetime.date.today().isoformat()
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            leituras = json.load(f)
    except Exception:
        leituras = []
    return next((l for l in leituras if l["data_envio"] == hoje), {"data": hoje, "texto": None, "info": "Nenhuma leitura encontrada"})

def enviar_leitura_do_dia():
    registro = get_versiculo_hoje()
    if registro.get("texto"):
        enviar_whatsapp(f"📖 Leitura do dia ({registro['data_envio']}):\n\n{registro['texto'][:4000]}")
    else:
        print(f"ℹ️ Nenhuma leitura encontrada para hoje ({registro['data']})")

# ---------------- ROTAS ----------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        texto_extraido = pytesseract.image_to_string(image, lang="por")
        salvar_leitura(texto_extraido)
        enviar_leitura_do_dia()
        return JSONResponse({"mensagem": "Imagem enviada, leitura salva e enviada pelo WhatsApp!", "texto_extraido": texto_extraido.strip()})
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)

@app.get("/versiculo-hoje")
async def versiculo_hoje():
    return JSONResponse(get_versiculo_hoje())

# ---------------- AGENDAMENTO AUTOMÁTICO ----------------
if BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(enviar_leitura_do_dia, "cron", hour=6, minute=0)
    scheduler.start()
    print("🕒 Agendador APScheduler iniciado com sucesso.")
else:
    print("🚫 Agendador desativado — APScheduler não instalado.")

# ---------------- EXECUÇÃO LOCAL ----------------
if __name__ == "__main__":
    import uvicorn
    enviar_leitura_do_dia()  # envia leitura do dia imediatamente
    uvicorn.run(app, host="0.0.0.0", port=5000)
