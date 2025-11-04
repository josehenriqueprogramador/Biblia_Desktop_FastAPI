import json
import datetime
import os
import urllib.request

# --- Configurações ---
# Pasta e arquivo JSON que contém o cronograma das leituras da semana
LEITURAS_JSON = "leituras/leituras.json"

# Bíblia principal
BIBLIA_JSON = "data/nvi.json"

# Configuração da API Z-API
INSTANCE_ID = "3E9A42A3E2CED133DB7B122EE267B15F"
TOKEN = "B515A074755027E95E2DD22E"
CLIENT_TOKEN = "F0d638864098645e1a66bdab8a41ec07aS"  # substitua pelo seu token completo

# Número destino (DDI + DDD + número)
NUMERO_DESTINO = "5521975682548"

# --- Função para pegar a leitura do dia ---
def leituras_do_dia():
    hoje = datetime.date.today().isoformat()
    if not os.path.exists(LEITURAS_JSON):
        print(f"⚠️ JSON de leituras não encontrado: {LEITURAS_JSON}")
        return None
    with open(LEITURAS_JSON, "r", encoding="utf-8") as f:
        leituras = json.load(f)
    leituras_hoje = [l for l in leituras if l.get("data_envio") == hoje]
    if not leituras_hoje:
        print("⚠️ Nenhuma leitura encontrada para hoje.")
        return None
    return leituras_hoje[0].get("texto", "")

# --- Função para buscar os versículos completos ---
def buscar_versiculos_do_texto(texto_ocr: str) -> str:
    if not os.path.exists(BIBLIA_JSON):
        print(f"❌ Arquivo da Bíblia não encontrado: {BIBLIA_JSON}")
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

# --- Função para enviar via WhatsApp usando Client-Token ---
def enviar_whatsapp(mensagem: str):
    url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}/send-text"
    payload = {
        "phone": NUMERO_DESTINO,
        "message": mensagem
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN
    }

    print("🔹 Payload que será enviado:", json.dumps(payload, indent=2))

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            print("Status HTTP:", response.status)
            print("Resposta Z-API:", response.read().decode("utf-8"))
    except Exception as e:
        print("❌ Erro ao enviar:", e)

# --- Fluxo principal ---
def main():
    print("=== Iniciando envio do versículo do dia ===")
    texto_ocr = leituras_do_dia()
    if not texto_ocr:
        print("Nenhuma leitura para hoje.")
        print("=== Fim do envio ===")
        return

    mensagem_final = buscar_versiculos_do_texto(texto_ocr)
    if not mensagem_final:
        print("Não foi possível gerar o texto completo da Bíblia para hoje.")
        print("=== Fim do envio ===")
        return

    print("Mensagem pronta para envio:\n")
    print(mensagem_final[:1000] + "\n...")
    enviar_whatsapp(mensagem_final)
    print("=== Fim do envio ===")

if __name__ == "__main__":
    main()
