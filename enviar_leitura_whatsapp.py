import json
import datetime
import requests
import os

# --- Configurações ---
BIBLIA_JSON = "data/nvi.json"
LEITURAS_JSON = "leituras/leituras.json"

# Configuração da API Z-API
WHATSAPP_API_URL = "https://api.z-api.io/instances/3E9A42A3E2CED133DB7B122EE267B15F/token/B515A074755027E95E2DD22E/send-text"
NUMERO_DESTINO = "5521920127396"

# --- Função para pegar a leitura do dia ---
def leituras_do_dia():
    hoje = datetime.date.today().isoformat()
    if not os.path.exists(LEITURAS_JSON):
        print("⚠️ JSON de leituras não encontrado:", LEITURAS_JSON)
        return None, {}
    with open(LEITURAS_JSON, "r", encoding="utf-8") as f:
        leituras = json.load(f)
    texto = leituras.get(hoje)
    if not texto:
        print("⚠️ Nenhuma leitura encontrada para hoje.")
        return None, leituras
    print(f"🔍 Leituras de {hoje} carregadas com sucesso.")
    return texto, leituras

# --- Função para buscar os versículos completos ---
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

# --- Função para enviar via WhatsApp ---
def enviar_whatsapp(mensagem: str):
    payload = {"phone": NUMERO_DESTINO, "message": mensagem}
    headers = {"Content-Type": "application/json"}
    print("Payload que será enviado:", payload)


    try:
        response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
        print("Status:", response.status_code)
        print("Resposta da Z-API:", response.text)
        if response.status_code == 200:
            print("✅ Mensagem enviada com sucesso!")
        else:
            print("❌ Não foi possível enviar a mensagem.")
    except Exception as e:
        print("❌ Erro ao enviar WhatsApp:", e)

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

    print("Mensagem pronta para envio (primeiros 1000 caracteres):\n")
    print(mensagem_final[:1000] + "\n...")

    # envia em blocos de até 1000 caracteres
    for i in range(0, len(mensagem_final), 1000):
        bloco = mensagem_final[i:i+1000]
        enviar_whatsapp(bloco)

    # remove os versículos do dia do JSON
    hoje = datetime.date.today().isoformat()
    if hoje in leituras:
        del leituras[hoje]
        os.makedirs("leituras", exist_ok=True)
        with open(LEITURAS_JSON, "w", encoding="utf-8") as f:
            json.dump(leituras, f, ensure_ascii=False, indent=2)
        print(f"🗑️ Versículos do dia {hoje} removidos do JSON.")

if __name__ == "__main__":
    main()
