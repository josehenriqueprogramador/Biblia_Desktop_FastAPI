import os
import json
import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Caminhos fixos
DATA_DIR = os.path.join(os.getcwd(), "data")
LEITURAS_DIR = os.path.join(os.getcwd(), "leituras")
NVI_DIR = os.path.join(DATA_DIR, "NVI")

os.makedirs(LEITURAS_DIR, exist_ok=True)

# Função utilitária para abrir JSON ignorando BOM
def load_json_utf8_sig(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

# Rota para upload de imagem (OCR)
@app.route("/upload", methods=["POST"])
def upload_image():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "Nenhuma imagem enviada"}), 400

    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    file.save(file_path)

    # Aqui entraria o OCR, mas simulamos leitura do texto
    texto_extraido = "DIA 01\n* Ezequiel 1:1 - 3:15 « Salmos 104:1-23\n* Provérbios 26:24-26 « Hebreus 3:1-19"
    data_envio = datetime.date.today().isoformat()

    leitura_path = os.path.join(LEITURAS_DIR, "versiculos.json")

    if os.path.exists(leitura_path):
        with open(leitura_path, "r", encoding="utf-8-sig") as f:
            todas = json.load(f)
    else:
        todas = []

    todas.append({"data_envio": data_envio, "texto": texto_extraido})

    with open(leitura_path, "w", encoding="utf-8") as f:
        json.dump(todas, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok", "data_envio": data_envio, "texto": texto_extraido})


# Rota para obter o versículo de hoje
@app.route("/versiculo-hoje", methods=["GET"])
def versiculo_hoje():
    hoje = datetime.date.today().isoformat()
    leitura_path = os.path.join(LEITURAS_DIR, "versiculos.json")

    if not os.path.exists(leitura_path):
        return jsonify({"data": hoje, "texto": None, "info": "Nenhuma leitura encontrada"})

    with open(leitura_path, "r", encoding="utf-8-sig") as f:
        leituras = json.load(f)

    texto_hoje = None
    for leitura in reversed(leituras):
        if leitura["data_envio"] == hoje:
            texto_hoje = leitura["texto"]
            break

    if not texto_hoje:
        return jsonify({"data": hoje, "texto": None, "info": "Nenhuma leitura encontrada"})

    return jsonify({"data": hoje, "texto": texto_hoje})


# Função para buscar um versículo na versão NVI
def buscar_versiculo(livro, capitulo, versiculos):
    arquivo = os.path.join(NVI_DIR, f"{livro.lower()}.json")
    if not os.path.exists(arquivo):
        return None
    data = load_json_utf8_sig(arquivo)
    cap = str(capitulo)
    if cap not in data:
        return None
    resultado = []
    for v in versiculos:
        texto = data[cap].get(str(v))
        if texto:
            resultado.append(f"{livro} {cap}:{v} - {texto}")
    return "\n".join(resultado) if resultado else None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
