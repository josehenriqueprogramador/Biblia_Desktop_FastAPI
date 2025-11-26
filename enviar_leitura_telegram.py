import json
import datetime
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# ===============================================================
# 🔧 CARREGAR VARIÁVEIS DO .env
# ===============================================================

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_DESTINO = os.getenv("CHAT_ID_DESTINO")

if not TELEGRAM_BOT_TOKEN or not CHAT_ID_DESTINO:
    raise Exception("❌ ERRO: TELEGRAM_BOT_TOKEN ou CHAT_ID_DESTINO não definidos no .env")

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# ===============================================================
# 🔧 IMPORTS OPCIONAIS (OCR)
# ===============================================================

try:
    from PIL import Image
except ImportError:
    import pip
    pip.main(['install', 'Pillow'])
    from PIL import Image

try:
    import pytesseract
except ImportError:
    import pip
    pip.main(['install', 'pytesseract'])
    import pytesseract


# ===============================================================
# 🔧 ESTRUTURA DE DIRETÓRIOS E ARQUIVOS
# ===============================================================

LEITURAS_DIR = "leituras"
LEITURAS_JSON = os.path.join(LEITURAS_DIR, "leituras.json")
BIBLIA_JSON = "data/nvi.json"

UPLOADS_DIR = "uploads"
PROCESSADAS_DIR = os.path.join(UPLOADS_DIR, "processadas")


# ===============================================================
# 📁 CRIAR PASTAS SE NÃO EXISTIREM
# ===============================================================

def garantir_estrutura():
    for pasta in [LEITURAS_DIR, UPLOADS_DIR, PROCESSADAS_DIR]:
        if not os.path.exists(pasta):
            os.makedirs(pasta)
            print(f"📂 Criada pasta: {pasta}")

    if not os.path.exists(LEITURAS_JSON):
        with open(LEITURAS_JSON, "w", encoding="utf-8") as f:
            json.dump([], f)
            print(f"📄 Criado JSON vazio: {LEITURAS_JSON}")


# ===============================================================
# 🔠 PROCESSAR IMAGENS → OCR → JSON
# ===============================================================

def processar_imagens_para_json():
    hoje = datetime.date.today().isoformat()
    leituras = []

    for img_path in Path(UPLOADS_DIR).glob("*.*"):
        if img_path.is_file():
            try:
                texto = pytesseract.image_to_string(Image.open(img_path), lang="por")

                if texto.strip():
                    leituras.append({"data_envio": hoje, "texto": texto.strip()})
                    print(f"✅ OCR realizado: {img_path}")

                destino = Path(PROCESSADAS_DIR) / img_path.name
                img_path.rename(destino)

            except Exception as e:
                print(f"❌ Erro ao processar {img_path}: {e}")

    if leituras:
        with open(LEITURAS_JSON, "w", encoding="utf-8") as f:
            json.dump(leituras, f, ensure_ascii=False, indent=2)
        print(f"📄 Atualizado JSON com leituras de hoje")
    else:
        print("⚠️ Nenhum texto extraído")


# ===============================================================
# 📖 BUSCAR LEITURA DO DIA
# ===============================================================

def leituras_do_dia():
    hoje = datetime.date.today().isoformat()

    try:
        with open(LEITURAS_JSON, "r", encoding="utf-8") as f:
            leituras = json.load(f)

        leituras_hoje = [l for l in leituras if l.get("data_envio") == hoje]

        if not leituras_hoje:
            print("⚠️ Nenhuma leitura encontrada para hoje.")
            return None

        return leituras_hoje[0].get("texto", "")

    except Exception as e:
        print("❌ Erro ao ler JSON:", e)
        return None


# ===============================================================
# 🕊️ GERAR TEXTO DA BÍBLIA A PARTIR DO OCR
# ===============================================================

def buscar_versiculos_do_texto(texto_ocr: str) -> str:
    if not os.path.exists(BIBLIA_JSON):
        print("❌ Arquivo da Bíblia não encontrado:", BIBLIA_JSON)
        return ""

    with open(BIBLIA_JSON, "r", encoding="utf-8") as f:
        biblia = json.load(f)

    resultado = []
    linhas = texto_ocr.splitlines()

    for linha in linhas:
        linha = linha.strip()
        if not linha or linha.startswith("DIA"):
            continue

        refs = linha.replace("+", ",").replace("«", ",").replace("e", ",").split(",")

        for ref in refs:
            ref = ref.strip()
            if not ref or " " not in ref:
                continue

            livro, resto = ref.split(" ", 1)

            if ":" in resto:
                cap, vers = resto.split(":")

                if "-" in vers:
                    inicio, fim = map(int, vers.split("-"))
                    for i in range(inicio, fim + 1):
                        texto = biblia.get(livro, {}).get(cap, {}).get(str(i), "")
                        if texto:
                            resultado.append(f"{livro} {cap}:{i} — {texto}")
                else:
                    texto = biblia.get(livro, {}).get(cap, {}).get(vers, "")
                    if texto:
                        resultado.append(f"{livro} {cap}:{vers} — {texto}")
            else:
                texto = biblia.get(livro, {}).get(resto, "")
                if texto:
                    resultado.append(f"{livro} {resto} — {texto}")

    return "\n".join(resultado)


# ===============================================================
# 📩 ENVIAR MENSAGEM PARA O TELEGRAM
# ===============================================================

def enviar_telegram(mensagem: str):
    payload = {
        "chat_id": CHAT_ID_DESTINO,
        "text": mensagem
    }

    try:
        r = requests.post(TELEGRAM_URL, json=payload)
        print("Status:", r.status_code)
        print("Resposta:", r.text)

        if r.status_code == 200:
            print("✅ Enviado com sucesso para o Telegram!")
        else:
            print("❌ Erro ao enviar")

    except Exception as e:
        print("❌ Erro na requisição:", e)


# ===============================================================
# ▶️ FLUXO PRINCIPAL
# ===============================================================

def main():
    print("=== Iniciando envio para o Telegram ===")

    garantir_estrutura()
    processar_imagens_para_json()

    texto_ocr = leituras_do_dia()
    if not texto_ocr:
        print("Nenhuma leitura hoje.")
        return

    mensagem_final = buscar_versiculos_do_texto(texto_ocr)
    if not mensagem_final:
        print("Erro ao gerar versículos.")
        return

    print("📤 Enviando para Telegram…")
    enviar_telegram(mensagem_final)

    print("=== Fim ===")


if __name__ == "__main__":
    main()
