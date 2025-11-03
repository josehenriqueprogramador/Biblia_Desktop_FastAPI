from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytesseract
from PIL import Image
import json, os, re, requests

app = FastAPI()

# ----------------------
# Diretórios
# ----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LEITURAS_DIR = os.path.join(BASE_DIR, "leituras")
os.makedirs(LEITURAS_DIR, exist_ok=True)

VERSICULOS_FILE = os.path.join(LEITURAS_DIR, "versiculos.json")

# ----------------------
# Função auxiliar
# ----------------------
def carregar_leituras():
    if os.path.exists(VERSICULOS_FILE):
        with open(VERSICULOS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def salvar_leituras(dados):
    with open(VERSICULOS_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# ----------------------
# Função: Enviar WhatsApp
# ----------------------
def enviar_whatsapp(mensagem):
    try:
        url = "https://api.z-api.io/instances/3E9A42A3E2CED133DB7B122EE267B15F/token/B515A074755027E95E2DD22E/send-text"
        data = {
            "phone": "5581999999999",  # <- coloque seu número completo com DDI
            "message": mensagem
        }
        response = requests.post(url, json=data)
        print("Resposta WhatsApp:", response.status_code, response.text)
    except Exception as e:
        print("Erro ao enviar WhatsApp:", e)

# ----------------------
# Função: Processar OCR
# ----------------------
def processar_texto(texto):
    padrao = re.compile(r"DIA\s*(\d{1,2})", re.IGNORECASE)
    partes = padrao.split(texto)

    leituras = {}
    for i in range(1, len(partes), 2):
        dia = partes[i].zfill(2)
        conteudo = partes[i+1].strip()
        if conteudo:
            leituras[dia] = conteudo
    return leituras

# ----------------------
# Endpoint principal
# ----------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <h2>Enviar imagem do cronograma</h2>
    <form action="/upload" enctype="multipart/form-data" method="post">
        <p>Envie uma imagem com as leituras (ex: "01/11 - João 1"). O sistema fará OCR e mostrará o texto extraído abaixo.</p>
        <input type="file" name="file">
        <input type="submit" value="Selecionar imagem">
    </form>
    """

@app.post("/upload")
async def upload(file: UploadFile):
    try:
        image = Image.open(file.file)
        texto = pytesseract.image_to_string(image, lang="por")
        leituras_extraidas = processar_texto(texto)

        if not leituras_extraidas:
            return {"erro": "Nenhum versículo identificado", "texto": texto}

        existentes = carregar_leituras()
        existentes.update(leituras_extraidas)
        salvar_leituras(existentes)

        return {
            "data_envio": datetime.now().strftime("%Y-%m-%d"),
            "texto": texto,
            "leituras_salvas": list(leituras_extraidas.keys())
        }
    except Exception as e:
        return {"erro": str(e)}

# ----------------------
# Endpoint: versículo de hoje
# ----------------------
@app.get("/versiculo-hoje")
def versiculo_hoje():
    hoje = datetime.now().strftime("%d")
    leituras = carregar_leituras()

    texto = leituras.get(hoje)
    if texto:
        return {"data": datetime.now().strftime("%Y-%m-%d"), "texto": texto}
    return {"data": datetime.now().strftime("%Y-%m-%d"), "texto": None, "info": "Nenhuma leitura encontrada"}

# ----------------------
# Scheduler (envio automático)
# ----------------------
def tarefa_diaria():
    hoje = datetime.now().strftime("%d")
    leituras = carregar_leituras()
    texto = leituras.get(hoje)
    if texto:
        enviar_whatsapp(f"📖 Versículo de hoje ({hoje}):\n{texto}")
    else:
        enviar_whatsapp("⚠️ Nenhuma leitura encontrada para hoje.")

scheduler = BackgroundScheduler()
scheduler.add_job(tarefa_diaria, "cron", hour=8, minute=0)  # envia às 08h
scheduler.start()

# ----------------------
# Inicialização
# ----------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
