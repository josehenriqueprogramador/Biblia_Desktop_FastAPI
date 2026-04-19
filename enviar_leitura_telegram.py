import json
import datetime
import requests
import os
import re # Adicionado para busca inteligente
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageEnhance # Adicionado ImageEnhance

# ===============================================================
# 🔧 CARREGAR VARIÁVEIS DO .env
# ===============================================================
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_DESTINO = os.getenv("CHAT_ID_DESTINO")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

try:
    import pytesseract
except ImportError:
    import pip
    pip.main(['install', 'pytesseract'])
    import pytesseract

# ===============================================================
# 🔧 CONFIGURAÇÕES DE PASTAS
# ===============================================================
LEITURAS_DIR = "leituras"
LEITURAS_JSON = os.path.join(LEITURAS_DIR, "leituras.json")
BIBLIA_JSON = "data/nvi.json"
UPLOADS_DIR = "uploads"
PROCESSADAS_DIR = os.path.join(UPLOADS_DIR, "processadas")

def garantir_estrutura():
    for pasta in [LEITURAS_DIR, UPLOADS_DIR, PROCESSADAS_DIR]:
        os.makedirs(pasta, exist_ok=True)
    if not os.path.exists(LEITURAS_JSON):
        with open(LEITURAS_JSON, "w", encoding="utf-8") as f:
            json.dump([], f)

# ===============================================================
# 🔠 PROCESSAR IMAGENS → OCR MELHORADO
# ===============================================================
def processar_imagens_para_json():
    hoje = datetime.date.today().isoformat()
    leituras = []

    for img_path in Path(UPLOADS_DIR).glob("*.*"):
        if img_path.is_file():
            try:
                # --- MELHORIA PARA IMAGEM DE ABRIL ---
                img = Image.open(img_path).convert('L') # Cinza
                img = ImageEnhance.Contrast(img).enhance(2.0) # Mais contraste
                # -------------------------------------
                
                texto = pytesseract.image_to_string(img, lang="por")

                if texto.strip():
                    leituras.append({"data_envio": hoje, "texto": texto.strip()})
                    print(f"✅ OCR realizado: {img_path.name}")

                destino = Path(PROCESSADAS_DIR) / img_path.name
                img_path.rename(destino)

            except Exception as e:
                print(f"❌ Erro ao processar {img_path}: {e}")

    if leituras:
        with open(LEITURAS_JSON, "w", encoding="utf-8") as f:
            json.dump(leituras, f, ensure_ascii=False, indent=2)

# ===============================================================
# 📖 BUSCAR LEITURA DO DIA (Mantido igual ao seu)
# ===============================================================
def leituras_do_dia():
    hoje = datetime.date.today().isoformat()
    try:
        with open(LEITURAS_JSON, "r", encoding="utf-8") as f:
            leituras = json.load(f)
        leituras_hoje = [l for l in leituras if l.get("data_envio") == hoje]
        return leituras_hoje[0].get("texto", "") if leituras_hoje else None
    except:
        return None

# ===============================================================
# 🕊️ BUSCAR VERSÍCULOS (VERSÃO ROBUSTA)
# ===============================================================
def buscar_versiculos_do_texto(texto_ocr: str) -> str:
    if not os.path.exists(BIBLIA_JSON): return ""
    with open(BIBLIA_JSON, "r", encoding="utf-8") as f:
        biblia = json.load(f)

    resultado = []
    # Regex que entende "1 Samuel 1:1", "João 3:16", "Ezequiel 31:1-32:32"
    # Ele separa o livro do resto pela última ocorrência de espaço antes do número
    padrao = re.compile(r"([1-3]?\s?[A-Z][a-zà-ÿ]+(?:\s[A-Z][a-zà-ÿ]+)?)\s(\d+):(\d+)(?:\s?-\s?(\d+))?")

    for match in padrao.finditer(texto_ocr):
        livro = match.group(1).strip()
        cap = match.group(2)
        v_inicio = int(match.group(3))
        v_fim = int(match.group(4)) if match.group(4) else v_inicio

        for v in range(v_inicio, v_fim + 1):
            texto = biblia.get(livro, {}).get(cap, {}).get(str(v))
            if texto:
                resultado.append(f"📖 {livro} {cap}:{v}\n{texto}")

    return "\n\n".join(resultado)

# ===============================================================
# 📩 ENVIAR MENSAGEM (Mantido igual ao seu)
# ===============================================================
def enviar_telegram(mensagem: str):
    if not mensagem: return
    try:
        requests.post(TELEGRAM_URL, json={"chat_id": CHAT_ID_DESTINO, "text": mensagem})
        print("✅ Enviado para o Telegram!")
    except Exception as e:
        print("❌ Erro no envio:", e)

# ===============================================================
# ▶️ FLUXO PRINCIPAL
# ===============================================================
def main():
    garantir_estrutura()
    processar_imagens_para_json()
    texto_ocr = leituras_do_dia()
    
    if texto_ocr:
        mensagem_final = buscar_versiculos_do_texto(texto_ocr)
        if mensagem_final:
            enviar_telegram(mensagem_final)
        else:
            print("⚠️ Nenhuma referência encontrada no texto.")
    else:
        print("⚠️ Nenhuma imagem para processar hoje.")

if __name__ == "__main__":
    main()
