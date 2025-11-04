import json
import datetime
import requests
import os

# --- Configurações ---
LEITURAS_JSON = "leituras/leituras.json"  # JSON com versículos da semana
BIBLIA_JSON = "data/nvi.json"             # Bíblia NVI

# Configuração da API Z-API
WHATSAPP_API_URL = "https://api.z-api.io/instances/SEU_INSTANCE/token/SEU_TOKEN/send-text"
NUMERO_DESTINO = "5521920127396"

# --- Função para pegar os versículos do dia ---
def leituras_do_dia():
    hoje = datetime.date.today().isoformat()
    print(f"🔍 Buscando leituras de {hoje} em {LEITURAS_JSON}...")

    if not os.path.exists(LEITURAS_JSON):
        print("❌ JSON de leituras não encontrado.")
        return None

    try:
        with open(LEITURAS_JSON, "r", encoding="utf-8") as f:
            leituras = json.load(f)  # JSON é um dict: { "YYYY-MM-DD": [versiculos] }

        texto_hoje = leituras.get(hoje)
        if not texto_hoje:
            print(f"⚠️ Nenhuma leitura encontrada para hoje ({hoje}).")
            return None

        return "\n".join(texto_hoje), leituras  # retorna também todo o JSON

    except Exception as e:
        print("❌ Erro ao ler JSON de leituras:", e)
        return None, {}

# --- Função para buscar os versículos completos na Bíblia ---
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
        if not linha or linha.upper().startswith("DIA"):
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

# --- Função para enviar via WhatsApp ---
def enviar_whatsapp(mensagem: str):
    payload = {"phone": NUMERO_DESTINO, "message": mensagem}
    headers = {"Content-Type": "application/json"}
    response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
    if response.status_code == 200:
        print("✅ Mensagem enviada com sucesso via Z-API!")
    else:
        print("❌ Erro ao enviar mensagem:", response.status_code, response.text)

# --- Fluxo principal ---
def main():
    texto_ocr, leituras = leituras_do_dia()
    if not texto_ocr:
        print("Nenhuma leitura para hoje.")
        return

    mensagem_final = buscar_versiculos_do_texto(texto_ocr)
    if not mensagem_final:
        print("Não foi possível gerar o texto completo da Bíblia para hoje.")
        return

    print("Mensagem pronta para envio:\n")
    print(mensagem_final[:1000] + "\n...")  # imprime os primeiros 1000 caracteres

    enviar_whatsapp(mensagem_final)

    # --- Remove os versículos do dia do JSON ---
    hoje = datetime.date.today().isoformat()
    if hoje in leituras:
        del leituras[hoje]
        with open(LEITURAS_JSON, "w", encoding="utf-8") as f:
            json.dump(leituras, f, ensure_ascii=False, indent=2)
        print(f"🗑️ Versículos do dia {hoje} removidos do JSON.")

if __name__ == "__main__":
    main()
