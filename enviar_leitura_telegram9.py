# -*- coding: utf-8-sig -*-
import os
import re
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID_DESTINO")

if not TOKEN or not CHAT_ID:
    raise Exception("ERRO: TELEGRAM_BOT_TOKEN ou CHAT_ID_DESTINO não encontrados no ambiente!")

URL_TELEGRAM = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
PROCESSADAS_DIR = UPLOADS_DIR / "processadas"

def garantir_estrutura():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSADAS_DIR.mkdir(parents=True, exist_ok=True)

LIVROS_CANONICOS = [
    "Gênesis","Êxodo","Levítico","Números","Deuteronômio","Josué","Juízes","Rute",
    "1 Samuel","2 Samuel","1 Reis","2 Reis","1 Crônicas","2 Crônicas","Esdras","Neemias",
    "Ester","Jó","Salmos","Provérbios","Eclesiastes","Cânticos","Isaías","Jeremias",
    "Lamentações","Ezequiel","Daniel","Oséias","Joel","Amós","Obadias","Jonas","Miquéias",
    "Naum","Habacuque","Sofonias","Ageu","Zacarias","Malaquias","Mateus","Marcos","Lucas",
    "João","Atos","Romanos","1 Coríntios","2 Coríntios","Gálatas","Efésios","Filipenses",
    "Colossenses","1 Tessalonicenses","2 Tessalonicenses","1 Timóteo","2 Timóteo","Tito",
    "Filemom","Hebreus","Tiago","1 Pedro","2 Pedro","1 João","2 João","3 João","Judas",
    "Apocalipse"
]

# Normalizações úteis para OCR antes de aplicar regex
NORMALIZACOES = {
    r"\bJoao\b": "João",
    r"\bJoäo\b": "João",
    r"\bJoâo\b": "João",
    r"\bJoa o\b": "João",
    r"\bJoÂo\b": "João",
    r"\bJoÃo\b": "João",
    r"\bProverbios\b": "Provérbios",
    r"\bProverbio\b": "Provérbios",
    r"\bEclesiastico\b": "Eclesiastes",
    r"\bOsEias\b": "Oséias",
    r"\bOseias\b": "Oséias",
    # numerais romanos com espaço
    r"\bI\s+João\b": "1 João",
    r"\bII\s+João\b": "2 João",
    r"\bIII\s+João\b": "3 João",
    r"\bI\s+Joao\b": "1 João",
    r"\bII\s+Joao\b": "2 João",
    r"\bIII\s+Joao\b": "3 João",
}

# Regex para encontrar referências completas: Livro CAP[:VERS] [- CAP[:VERS]]
def livro_regex_component(nome: str) -> str:
    n = re.escape(nome)
    n = n.replace(r"\ ", r"\s+")
    return n

LIVROS_REGEX = "|".join(livro_regex_component(l) for l in LIVROS_CANONICOS)

REGEX_REF_COMPLETA = re.compile(
    rf"(?P<livro>{LIVROS_REGEX})\s*(?P<c1>\d+)\s*(?:[:]\s*(?P<v1>\d+))?\s*(?:[-–—]\s*(?P<c2>\d+)(?:\s*[:]\s*(?P<v2>\d+))?)?",
    re.IGNORECASE,
)

# Regex para capturar números curtos como "2:18" ou "3:6" que dependem do livro anterior
REGEX_NUM_SHORT = re.compile(r"(?P<c>\d+)(?:\s*[:]\s*(?P<v>\d+))?(?:\s*[-–—]\s*(?P<c2>\d+)(?:\s*[:]\s*(?P<v2>\d+))?)?")

# Separadores - usamos para dividir segmentos (bullets, quebras, pontos e vírgulas)
SEGMENT_SPLIT_RE = re.compile(r"[•\*\+\n;/\u2022]+")

# Separador usado para indicar intervalo com hífen; guardamos pra montagem
SEP_PATTERN = r"[-+–—]+"

def _apply_normalizacoes_no_texto(texto: str) -> str:
    t = texto
    for k, v in NORMALIZACOES.items():
        try:
            t = re.sub(k, v, t, flags=re.IGNORECASE)
        except re.error:
            t = re.sub(re.escape(k), v, t, flags=re.IGNORECASE)
    # espaços extras -> simples
    t = re.sub(r"[ ]{2,}", " ", t)
    return t

def normalizar_livro(texto: str) -> str:
    t = (texto or "").strip()
    t = re.sub(r"\s+", " ", t)
    for k, v in NORMALIZACOES.items():
        try:
            t = re.sub(k, v, t, flags=re.IGNORECASE)
        except re.error:
            t = re.sub(re.escape(k), v, t, flags=re.IGNORECASE)
    t = t[0].upper() + t[1:] if t else t
    t = re.sub(r"^(1|2|3)\s*(Joao|João)$", r"\1 João", t, flags=re.IGNORECASE)
    t = re.sub(r"^(1|2|3)(Joao|João)$", r"\1 João", t, flags=re.IGNORECASE)
    for livro in LIVROS_CANONICOS:
        if re.fullmatch(re.escape(livro), t, flags=re.IGNORECASE):
            return livro
        plain = re.sub(r"[^A-Za-z0-9 ]+", "", livro).lower()
        cand = re.sub(r"[^A-Za-z0-9 ]+", "", t).lower()
        if plain == cand:
            return livro
    return t

def _parse_ref_str(ref_str: str):
    # tenta parsear "Livro C:V-C:V" ou "Livro C:V-V" ou "Livro C:V"
    m = re.match(r"^(?P<book>.+?)\s+(?P<c1>\d+):(?P<v1>\d+)(?:-(?:(?P<c2>\d+):)?(?P<v2>\d+))?$", ref_str)
    if m:
        book = normalizar_livro(m.group("book"))
        c1 = int(m.group("c1"))
        v1 = int(m.group("v1"))
        if m.group("c2"):
            c2 = int(m.group("c2"))
            v2 = int(m.group("v2"))
        else:
            c2 = c1
            v2 = int(m.group("v2")) if m.group("v2") else None
        return (book, (c1, v1), (c2, v2 if v2 is not None else None))
    # tentar "Livro C:V-E" (ex: Salmos 121:1-8)
    m2 = re.match(r"^(?P<book>.+?)\s+(?P<c1>\d+):(?P<v1>\d+)-(?P<end>\d+)$", ref_str)
    if m2:
        book = normalizar_livro(m2.group("book"))
        c1 = int(m2.group("c1"))
        v1 = int(m2.group("v1"))
        c2 = c1
        v2 = int(m2.group("end"))
        return (book, (c1, v1), (c2, v2))
    return None

def _pos_leq(a, b):
    return (a[0] < b[0]) or (a[0] == b[0] and a[1] <= b[1])

def _pos_geq(a, b):
    return (a[0] > b[0]) or (a[0] == b[0] and a[1] >= b[1])

def _covers(ref_long, ref_short):
    if not ref_long or not ref_short:
        return False
    book_l, start_l, end_l = ref_long[0], ref_long[1], ref_long[2]
    book_s, start_s, end_s = ref_short[0], ref_short[1], ref_short[2]
    if book_l.lower() != book_s.lower():
        return False
    end_l_norm = end_l if (end_l and end_l[1] is not None) else (end_l[0], 9999) if end_l else (start_l[0], 9999)
    end_s_norm = end_s if (end_s and end_s[1] is not None) else (end_s[0], 9999) if end_s else (start_s[0], 9999)
    return _pos_leq(start_l, start_s) and _pos_geq(end_l_norm, end_s_norm)

def montar_intervalo(livro_raw: str, c1: str, v1: str | None, c2: str | None, v2: str | None) -> str:
    livro = normalizar_livro(livro_raw)
    try:
        c1_i = int(c1)
    except Exception:
        c1_i = 1
    v1_i = int(v1) if v1 and v1.isdigit() else 1
    if not c2:
        return f"{livro} {c1_i}:{v1_i}"
    try:
        c2_i = int(c2)
    except Exception:
        c2_i = c1_i
    # CASO: mesmo capítulo -> simplificar 121:1-8
    if c1_i == c2_i:
        v2_i = int(v2) if v2 and v2.isdigit() else None
        if v2_i is not None:
            return f"{livro} {c1_i}:{v1_i}-{v2_i}"
        return f"{livro} {c1_i}:{v1_i}-{c2_i}"
    # Entre capítulos, se v2 existe -> Daniel 9:1-11:1
    if v2 and v2.isdigit():
        v2_i = int(v2)
        return f"{livro} {c1_i}:{v1_i}-{c2_i}:{v2_i}"
    # Entre capítulos sem v2 -> Daniel 9:1-11
    return f"{livro} {c1_i}:{v1_i}-{c2_i}"

def ocr_extrair_texto(img_path: Path):
    from PIL import Image
    import pytesseract
    texto = pytesseract.image_to_string(Image.open(img_path), lang="por")
    linhas = [ln.rstrip() for ln in texto.splitlines() if ln.strip()]
    return "\n".join(linhas)

def extrair_referencias_do_bloco(texto_ocr: str, dia_atual: int) -> list[str]:
    bloco_re = re.compile(rf"DIA\s+0*{dia_atual}\b(.*?)(?=\bDIA\s+\d+|\Z)", re.IGNORECASE | re.DOTALL)
    m = bloco_re.search(texto_ocr)
    if not m:
        return []
    trecho = m.group(1)
    # substituir bullets/sinais por quebras para segmentar melhor
    trecho = trecho.replace("•", "\n").replace("*", "\n").replace("+", "\n")
    trecho = re.sub(r"[^\S\r\n]+", " ", trecho)
    trecho_norm = _apply_normalizacoes_no_texto(trecho)
    referencias = []
    # 1) capturar referências completas (com nome do livro)
    for mm in REGEX_REF_COMPLETA.finditer(trecho_norm):
        livro = mm.group("livro")
        c1 = mm.group("c1")
        v1 = mm.group("v1")
        c2 = mm.group("c2")
        v2 = mm.group("v2")
        ref = montar_intervalo(livro, c1, v1, c2, v2)
        referencias.append(ref)
    # 2) segments: dividir por linhas e ';' para pegar segmentos como "Provérbios 28:27-28 - 1 João 2:18 - 3:6"
    segments = [seg.strip() for seg in re.split(r"[\n;]+", trecho_norm) if seg.strip()]
    for seg in segments:
        last_book = None
        for mm in REGEX_REF_COMPLETA.finditer(seg):
            last_book = normalizar_livro(mm.group("livro"))
        if not last_book:
            m_book = re.match(rf"(?P<book>{LIVROS_REGEX})", seg, flags=re.IGNORECASE)
            if m_book:
                last_book = normalizar_livro(m_book.group("book"))
        if not last_book:
            continue
        # procurar padrões numéricos curtos na mesma segment
        for sm in REGEX_NUM_SHORT.finditer(seg):
            c = sm.group('c')
            v = sm.group('v')
            c2 = sm.group('c2')
            v2 = sm.group('v2')
            span = sm.span()
            inside_full = False
            for full in REGEX_REF_COMPLETA.finditer(seg):
                if full.start() <= span[0] and full.end() >= span[1]:
                    inside_full = True
                    break
            if inside_full:
                continue
            try:
                ref_candidate = montar_intervalo(last_book, c, v, c2, v2)
            except Exception:
                continue
            parsed_candidate = _parse_ref_str(ref_candidate)
            covered = False
            for existing in referencias:
                parsed_existing = _parse_ref_str(existing)
                if _covers(parsed_existing, parsed_candidate):
                    covered = True
                    break
            if not covered and ref_candidate not in referencias:
                referencias.append(ref_candidate)
    # dedupe mantendo ordem
    resultado = []
    seen = set()
    for r in referencias:
        key = r.lower()
        if key not in seen:
            seen.add(key)
            resultado.append(r)
    # filtro final: remover capturas estranhas (cap <=0 etc.)
    filtered = []
    for r in resultado:
        m = re.match(r"^(?P<book>.+?)\s+(?P<c>\d+):(?P<v>\d+)(?:-(?P<c2>\d+)(?::(?P<v2>\d+))?)?$", r)
        if not m:
            filtered.append(r)
            continue
        c = int(m.group("c"))
        if c <= 0:
            continue
        filtered.append(r)
    return filtered

def enviar_telegram(referencias: list[str]):
    hoje = datetime.now().strftime("%d/%m/%Y")
    if not referencias:
        print("Nenhuma referência para enviar.")
        return False
    mensagem = f"Leitura de Hoje ({hoje})\n\n"
    for r in referencias:
        mensagem += f"• {r}\n"
    mensagem += "\nVeja a leitura completa em:\nhttps://biblia-desktop.onrender.com"
    resp = requests.post(URL_TELEGRAM, data={"chat_id": CHAT_ID, "text": mensagem})
    print("Status:", resp.status_code)
    print("Resposta:", resp.text)
    return resp.ok

def processar_imagem(caminho_imagem: Path) -> bool:
    print("Processando", caminho_imagem)
    texto_bruto = ocr_extrair_texto(caminho_imagem)
    print("--- TEXTO OCR BRUTO ---")
    print(texto_bruto)
    print("-----------------------")
    dia_atual = int(datetime.now().strftime("%d"))
    referencias = extrair_referencias_do_bloco(texto_bruto, dia_atual)
    print("Referências extraídas:", referencias)
    if not referencias:
        print("Nenhuma referência encontrada para o dia atual.")
        return False
    enviado = enviar_telegram(referencias)
    return enviado

def processar_upload(caminho: str) -> bool:
    caminho_path = Path(caminho)
    if not caminho_path.exists():
        print("Arquivo não encontrado:", caminho)
        return False
    sucesso = processar_imagem(caminho_path)
    destino = PROCESSADAS_DIR / caminho_path.name
    try:
        caminho_path.rename(destino)
        try:
            destino.unlink()
            print("Arquivo processado destruído:", destino)
        except:
            pass
    except Exception as e:
        print("Erro movendo arquivo para processadas:", e)
    return sucesso

def main():
    garantir_estrutura()
    hoje_dia = int(datetime.now().strftime("%d"))
    print(f"DIA ATUAL DETECTADO: {hoje_dia}")
    any_processed = False
    for img_path in sorted(UPLOADS_DIR.glob("*.*")):
        if not img_path.is_file():
            continue
        if img_path.parent.name == "processadas":
            continue
        print()
        print(f"Iniciando processamento de: {img_path.name}")
        try:
            enviado = processar_imagem(img_path)
            any_processed = any_processed or enviado
        except Exception as e:
            print("Erro durante processamento:", e)
            enviado = False
        destino = PROCESSADAS_DIR / img_path.name
        try:
            img_path.rename(destino)
            print(f"Movido para {destino}")
        except Exception as e:
            print("Erro movendo arquivo:", e)
    if not any_processed:
        print("INFO: Nenhuma leitura enviada nesta execução.")
    print("=== Fim do processamento diário ===")

if __name__ == "__main__":
    main()
