import json
import datetime
import requests
import os

# --- Configurações ---
URL_LEITURAS = "https://biblia-desktop-fastapi.onrender.com/leituras.json"
BIBLIA_JSON = "data/biblia.json"

# Configuração da API Z-API
WHATSAPP_API_URL = "https://api.z-api.io/instances/3E9A42A3E2CED133DB7B122EE267B15F/token/B515A074755027E95E2DD22E/send-text"
NUMERO_DESTINO = "5521920127396"

# --- Função para pegar a leitura do dia (baixando do Render) ---
def leituras_do_dia():
    hoje = datetime.date.today().isoformat()
    print(f"🔍 Buscando leituras de {hoje} em {URL_LEITURAS}...")
    try:
        resp = requests.get(URL_LEITURAS, timeout=10)
        if resp.status_code != 200:
            print("❌ Erro ao baixar leituras:", resp.status_code)
            return None
        leituras = resp.json()
        leituras_hoje = [l for l in leituras if l["data_envio"] == hoje]
        if not leituras_hoje:
            print("⚠️ Nenhuma leitura encontrada para hoje.")
            return None
        return leituras_hoje[0]["texto"]
    except Exception as e:
        print("❌ Erro ao obter leituras:", e)
        return None

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
    response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
    if response.status_code == 200:
        print("✅ Mensagem enviada com sucesso via Z-API!")
    else:
        print("❌ Erro ao enviar mensagem:", response.status_code, response.text)

# --- Fluxo principal ---
def main():
    texto_ocr = leituras_do_dia()
    if not texto_ocr:
        print("Nenhuma leitura para hoje.")
        return
    
    mensagem_final = buscar_versiculos_do_texto(texto_ocr)
    if not mensagem_final:
        print("Não foi possível gerar o texto completo da Bíblia para hoje.")
        return
    
    print("Mensagem pronta para envio:\n")
    print(mensagem_final[:1000] + "\n...")
    enviar_whatsapp(mensagem_final)

if __name__ == "__main__":
    main()
