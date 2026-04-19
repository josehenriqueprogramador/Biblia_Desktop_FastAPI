import json
import datetime
import requests
import os
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageEnhance # Adicionado apenas ImageEnhance

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_DESTINO = os.getenv("CHAT_ID_DESTINO")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

import pytesseract

# Se estiver no Render, precisamos garantir que o Tesseract seja encontrado
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

LEITURAS_DIR = "leituras"
LEITURAS_JSON = os.path.join(LEITURAS_DIR, "leituras.json")
BIBLIA_JSON = "data/nvi.json"
UPLOADS_DIR = "uploads"
PROCESSADAS_DIR = os.path.join(UPLOADS_DIR, "processadas")

def garantir_estrutura():
    for pasta in [LEITURAS_DIR, UPLOADS_DIR, PROCESSADAS_DIR]:
        if not os.path.exists(pasta):
            os.makedirs(pasta)
    if not os.path.exists(LEITURAS_JSON):
        with open(LEITURAS_JSON, "w", encoding="utf-8") as f:
            json.dump([], f)

def processar_imagens_para_json():
    hoje = datetime.date.today().isoformat()
    leituras = []
    for img_path in Path(UPLOADS_DIR).glob("*.*"):
        if img_path.is_file():
            try:
                # O PULO DO GATO: Aumentar o contraste para o fundo azul de Abril
                img = Image.open(img_path).convert('L')
                img = ImageEnhance.Contrast(img).enhance(2.0) 
                
                texto = pytesseract.image_to_string(img, lang="por")

                if texto.strip():
                    leituras.append({"data_envio": hoje, "texto": texto.strip()})
                
                destino = Path(PROCESSADAS_DIR) / img_path.name
                img_path.rename(destino)
            except Exception as e:
                print(f"Erro: {e}")

    if leituras:
        with open(LEITURAS_JSON, "w", encoding="utf-8") as f:
            json.dump(leituras, f, ensure_ascii=False, indent=2)

def leituras_do_dia():
    hoje = datetime.date.today().isoformat()
    try:
        with open(LEITURAS_JSON, "r", encoding="utf-8") as f:
            leituras = json.load(f)
        leituras_hoje = [l for l in leituras if l.get("data_envio") == hoje]
        return leituras_hoje[0].get("texto", "") if leituras_hoje else None
    except:
        return None

def buscar_versiculos_do_texto(texto_ocr: str) -> str:
    if not os.path.exists(BIBLIA_JSON): return ""
    with open(BIBLIA_JSON, "r", encoding="utf-8") as f:
        biblia = json.load(f)
    
    resultado = []
    linhas = texto_ocr.splitlines()
    for linha in linhas:
        linha = linha.strip()
        if not linha or linha.startswith("DIA"): continue
        
        # Sua lógica original de split por vírgula
        refs = linha.replace("+", ",").replace("«", ",").replace("e", ",").split(",")
        for ref in refs:
            ref = ref.strip()
            if not ref or " " not in ref: continue
            try:
                livro, resto = ref.split(" ", 1)
                if ":" in resto:
                    cap, vers = resto.split(":")
                    if "-" in vers:
                        inicio, fim = map(int, vers.split("-"))
                        for i in range(inicio, fim + 1):
                            t = biblia.get(livro, {}).get(cap, {}).get(str(i))
                            if t: resultado.append(f"{livro} {cap}:{i} — {t}")
                    else:
                        t = biblia.get(livro, {}).get(cap, {}).get(vers)
                        if t: resultado.append(f"{livro} {cap}:{vers} — {t}")
            except: continue
    return "\n".join(resultado)

def enviar_telegram(mensagem: str):
    requests.post(TELEGRAM_URL, json={"chat_id": CHAT_ID_DESTINO, "text": mensagem})

def main():
    garantir_estrutura()
    processar_imagens_para_json()
    texto = leituras_do_dia()
    if texto:
        msg = buscar_versiculos_do_texto(texto)
        if msg: enviar_telegram(msg)

if __name__ == "__main__":
    main()
