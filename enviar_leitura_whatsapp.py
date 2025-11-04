import json
import datetime
import requests
import os
from pathlib import Path
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

# --- Configurações ---
LEITURAS_DIR = "leituras"
LEITURAS_JSON = os.path.join(LEITURAS_DIR, "leituras.json")
BIBLIA_JSON = "data/nvi.json"
UPLOADS_DIR = "uploads"
PROCESSADAS_DIR = os.path.join(UPLOADS_DIR, "processadas")

# Configuração da API Z-API
WHATSAPP_API_URL = "https://api.z-api.io/instances/3E9A42A3E2CED133DB7B122EE267B15F/send-text"
NUMERO_DESTINO = "5521920127396"
CLIENT_TOKEN = "F0d638864098645e1a66bdab8a41ec07aS"  # Substitua pelo seu token

# --- Funções ---
def garantir_estrutura():
    for pasta in [LEITURAS_DIR, UPLOADS_DIR, PROCESSADAS_DIR]:
        if not os.path.exists(pasta):
            os.makedirs(pasta)
            print(f"📂 Criada pasta {pasta}")
    if not os.path.exists(LEITURAS_JSON):
        with open(LEITURAS_JSON, "w", encoding="utf-8") as f:
            json.dump([], f)
        print(f"📄 Criado arquivo JSON vazio {LEITURAS_JSON}")

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
                # Move a imagem para processadas
                destino = Path(PROCESSADAS_DIR) / img_path.name
                img_path.rename(destino)
            except Exception as e:
                print(f"❌ Erro ao processar {img_path}: {e}")
    if leituras:
        with open(LEITURAS_JSON, "w", encoding="utf-8") as f:
            json.dump(leituras, f, ensure_ascii=False, indent=2)
        print(f"📄 Atualizado {LEITURAS_JSON} com as leituras do dia")
    else:
        print("⚠️ Nenhum texto extraído das imagens")

def leituras_do_dia():
    hoje = datetime.date.today().isoformat()
    print(f"🔍 Buscando leituras de {hoje} em {LEITURAS_JSON}...")
    try:
        with open(LEITURAS_JSON, "r", encoding="utf-8") as f:
            leituras = json.load(f)
        leituras_hoje = [l for l in leituras if l.get("data_envio") == hoje]
        if not leituras_hoje:
            print("⚠️ Nenhuma leitura encontrada para hoje.")
            return None
        print("✅ Leitura encontrada para hoje.")
        return leituras_hoje[0].get("texto", "")
    except Exception as e:
        print("❌ Erro ao ler JSON:", e)
        return None

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
                    for i in range(inicio, fim+1):
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

def enviar_whatsapp(mensagem: str):
    payload = {"phone": NUMERO_DESTINO, "message": mensagem}
    print("📤 Payload que será enviado:", payload)
    headers = {
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN
    }
    try:
        response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
        print("Status HTTP:", response.status_code)
        print("Resposta Z-API:", response.text)
        if response.status_code == 200:
            print("✅ Mensagem enviada com sucesso via Z-API!")
        else:
            print("❌ Erro ao enviar mensagem:", response.status_code)
    except Exception as e:
        print("❌ Erro na requisição:", e)

# --- Fluxo principal ---
def main():
    print("=== Iniciando envio do versículo do dia ===")
    garantir_estrutura()
    processar_imagens_para_json()  # <- executa OCR antes de buscar leitura
    texto_ocr = leituras_do_dia()
    if not texto_ocr:
        print("Nenhuma leitura para hoje.")
        print("=== Fim do envio ===")
        return

    mensagem_final = buscar_versiculos_do_texto(texto_ocr)
    if not mensagem_final:
        print("❌ Não foi possível gerar o texto completo da Bíblia para hoje.")
        print("=== Fim do envio ===")
        return

    print("Mensagem pronta para envio:\n")
    print(mensagem_final[:1000] + "\n...")
    enviar_whatsapp(mensagem_final)
    print("=== Fim do envio ===")

if __name__ == "__main__":
    main()
