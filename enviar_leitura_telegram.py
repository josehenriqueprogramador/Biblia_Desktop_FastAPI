import json
import datetime
import requests
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageEnhance
import pytesseract

# ===============================================================
# 🔧 CONFIGURAÇÕES E PASTAS
# ===============================================================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_DESTINO = os.getenv("CHAT_ID_DESTINO")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

LEITURAS_DIR = "leituras"
LEITURAS_JSON = os.path.join(LEITURAS_DIR, "leituras.json")
BIBLIA_JSON = "data/nvi.json"
UPLOADS_DIR = "uploads"
PROCESSADAS_DIR = os.path.join(UPLOADS_DIR, "processadas")

LIVROS = [
    "Gênesis","Êxodo","Levítico","Números","Deuteronômio","Josué","Juízes","Rute",
    "1 Samuel","2 Samuel","1 Reis","2 Reis","1 Crônicas","2 Crônicas","Esdras",
    "Neemias","Ester","Jó","Salmos","Provérbios","Eclesiastes","Cânticos","Isaías",
    "Jeremias","Lamentações","Ezequiel","Daniel","Oséias","Joel","Amós","Obadias",
    "Jonas","Miquéias","Naum","Habacuque","Sofonias","Ageu","Zacarias","Malaquias",
    "Mateus","Marcos","Lucas","João","Atos","Romanos","1 Coríntios","2 Coríntios",
    "Gálatas","Efésios","Filipenses","Colossenses","1 Tessalonicenses",
    "2 Tessalonicenses","1 Timóteo","2 Timóteo","Tito","Filemom","Hebreus",
    "Tiago","1 Pedro","2 Pedro","1 João","2 João","3 João","Judas","Apocalipse",
    "Joao" # Fallback para erros de OCR
]

# ===============================================================
# 🧠 LÓGICA DE EXTRAÇÃO (REGEX)
# ===============================================================

def normalizar_livro_para_regex(nome):
    """Cria regex flexível para livros com números (Ex: 1 Samuel, I Samuel)."""
    nome_original = nome.strip()
    m = re.match(r"^\s*([1-3]|I{1,3})\s+(.*)$", nome_original, flags=re.IGNORECASE)
    if m:
        parte_numeral = r"(?:[1-3]|I{1,3}|[1-3]°)?\\s*"
        parte_nome = re.escape(m.group(2))
    else:
        parte_numeral = ""
        parte_nome = re.escape(nome_original)
    
    return parte_numeral + re.sub(r"\\ ", r"\\s*", parte_nome)

LIVROS_REGEX = "|".join(normalizar_livro_para_regex(l) for l in LIVROS)

# Captura referências mesmo coladas em símbolos (Ex: •Josué)
REGEX_REF = re.compile(
    rf"((?:{LIVROS_REGEX})\s*\d+\s*[:]\s*\d+(?:\s*[-–—]\s*\d+)?)",
    re.IGNORECASE,
)

# ===============================================================
# 🖼️ PRÉ-PROCESSAMENTO (O segredo para a imagem de Abril)
# ===============================================================

def ocr_com_binarizacao(img_path: Path):
    """Transforma a imagem em P&B puro para destacar texto claro em fundo colorido."""
    img = Image.open(img_path)
    gray = img.convert('L') # Escala de cinza
    
    # Aumenta contraste
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(2.0)
    
    # Binarização (Threshold): O que for claro vira branco, o que for escuro vira preto
    # Isso isola o texto branco/amarelo do fundo azul claro da imagem de Abril
    img_bin = gray.point(lambda x: 0 if x < 140 else 255, '1')
    
    return pytesseract.image_to_string(img_bin, lang="por")

# ===============================================================
# 🕊️ BUSCAR TEXTO NA BÍBLIA
# ===============================================================

def extrair_referencias_do_dia(texto_ocr: str, dia: int) -> list:
    """Filtra o texto para pegar apenas as referências do dia atual."""
    referencias = []
    coletando = False
    
    padrao_inicio = re.compile(rf"\bD\s*I\s*A\s*0*{dia}\b", re.IGNORECASE)
    padrao_fim = re.compile(rf"\bD\s*I\s*A\s*0*{dia + 1}\b", re.IGNORECASE)

    for linha in texto_ocr.splitlines():
        if padrao_inicio.search(linha):
            coletando = True
        elif coletando and padrao_fim.search(linha):
            break
        
        if coletando:
            encontrados = REGEX_REF.findall(linha)
            for ref in encontrados:
                # Normalização básica
                ref_norm = re.sub(r"\s+", " ", ref).replace(" : ", ":")
                referencias.append(ref_norm.strip())
    
    return list(dict.fromkeys(referencias)) # Remove duplicatas

def buscar_texto_biblico(referencias: list) -> str:
    if not os.path.exists(BIBLIA_JSON) or not referencias:
        return ""

    with open(BIBLIA_JSON, "r", encoding="utf-8") as f:
        biblia = json.load(f)

    resultado = []
    for ref in referencias:
        try:
            # Tenta separar Livro de Capítulo:Versículo
            partes = ref.rsplit(" ", 1)
            livro = partes[0]
            cap_vers = partes[1]
            
            cap, vers = cap_vers.split(":")
            
            if "-" in vers:
                inicio, fim = map(int, vers.replace("–", "-").split("-"))
                for i in range(inicio, fim + 1):
                    texto = biblia.get(livro, {}).get(cap, {}).get(str(i), "")
                    if texto: resultado.append(f"📖 {livro} {cap}:{i}\n{texto}")
            else:
                texto = biblia.get(livro, {}).get(cap, {}).get(vers, "")
                if texto: resultado.append(f"📖 {livro} {cap}:{vers}\n{texto}")
        except:
            continue

    return "\n\n".join(resultado)

# ===============================================================
# ▶️ FLUXO PRINCIPAL
# ===============================================================

def main():
    garantir_estrutura() # Reaproveite sua função de criar pastas
    hoje = datetime.date.today()
    dia_atual = hoje.day
    
    print(f"🔍 Buscando leitura para o DIA {dia_atual}...")

    for img_path in Path(UPLOADS_DIR).glob("*.*"):
        if img_path.is_file() and not img_path.name.startswith("leitura_"):
            print(f"📸 Processando imagem: {img_path.name}")
            
            texto_ocr = ocr_com_binarizacao(img_path)
            referencias = extrair_referencias_do_dia(texto_ocr, dia_atual)
            
            if referencias:
                print(f"✅ Referências encontradas: {referencias}")
                mensagem = buscar_texto_biblico(referencias)
                
                if mensagem:
                    enviar_telegram(mensagem)
                    # Opcional: Salvar no JSON para cache
                
                # Move para processadas
                img_path.rename(Path(PROCESSADAS_DIR) / img_path.name)
            else:
                print(f"⚠️ Nenhuma referência encontrada no DIA {dia_atual}")

def garantir_estrutura():
    for pasta in [LEITURAS_DIR, UPLOADS_DIR, PROCESSADAS_DIR]:
        os.makedirs(pasta, exist_ok=True)

def enviar_telegram(mensagem: str):
    requests.post(TELEGRAM_URL, json={"chat_id": CHAT_ID_DESTINO, "text": mensagem})

if __name__ == "__main__":
    main()
