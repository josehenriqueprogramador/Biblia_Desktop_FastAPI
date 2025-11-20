import json
import mysql.connector
import os

# =============================
# CONFIGURAÇÕES DO BANCO
# =============================
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',  # ou sua senha
    'database': 'bible',
    'charset': 'utf8mb4'
}

# =============================
# DIRETÓRIO DOS JSONS
# =============================
DATA_DIR = '.'  # Android/Termux
# DATA_DIR = '/home/jose/biblia_app/data'         # Linux/Ubuntu

# =============================
# CONEXÃO
# =============================
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

# =============================
# FUNÇÃO: OBTER OU CRIAR VERSÃO
# =============================
def get_or_create_version(code, name=None, language='pt'):
    cursor.execute("SELECT id FROM versions WHERE code=%s", (code,))
    row = cursor.fetchone()
    if row:
        return row[0]
    # Se não existir, cria automaticamente
    cursor.execute(
        "INSERT INTO versions (code, name, language) VALUES (%s,%s,%s)",
        (code, name or code, language)
    )
    conn.commit()
    version_id = cursor.lastrowid
    print(f"Versão criada: {code} (id={version_id})")
    return version_id

# =============================
# FUNÇÃO: IMPORTAR JSON PARA O BANCO
# =============================
def importar_biblia(json_file, version_code):
    # Pega ou cria a versão
    version_id = get_or_create_version(version_code)
    
    # Carrega JSON
    with open(json_file, 'r', encoding='utf-8-sig') as f:
        biblia_json = json.load(f)
    
    for order_index, livro_data in enumerate(biblia_json, 1):
        abbrev = livro_data['abbrev']
        name = livro_data.get('name', abbrev.capitalize())
        
        # Verifica se livro já existe
        cursor.execute(
            "SELECT id FROM books WHERE version_id=%s AND abbrev=%s",
            (version_id, abbrev)
        )
        book_row = cursor.fetchone()
        if book_row:
            book_id = book_row[0]
            print(f"Livro existente: {name} ({abbrev})")
        else:
            # Insere livro
            cursor.execute(
                "INSERT INTO books (version_id, abbrev, name, order_index) VALUES (%s,%s,%s,%s)",
                (version_id, abbrev, name, order_index)
            )
            book_id = cursor.lastrowid
            print(f"Livro inserido: {name} ({abbrev})")
        
        # Inserir capítulos e versículos
        for chapter_number, chapter in enumerate(livro_data['chapters'], 1):
            cursor.execute(
                "INSERT INTO chapters (book_id, chapter_number) VALUES (%s,%s)",
                (book_id, chapter_number)
            )
            chapter_id = cursor.lastrowid
            
            for verse_number, verse_text in enumerate(chapter, 1):
                cursor.execute(
                    "INSERT INTO verses (chapter_id, verse_number, text) VALUES (%s,%s,%s)",
                    (chapter_id, verse_number, verse_text)
                )
    
    conn.commit()
    print(f"Importação da versão {version_code} concluída!\n")

# =============================
# LOOP PARA TODOS OS JSONS
# =============================
for filename in os.listdir(DATA_DIR):
    if filename.endswith('.json'):
        code = filename.replace('.json','').upper()
        print(f"Iniciando importação: {filename}")
        importar_biblia(os.path.join(DATA_DIR, filename), code)

# =============================
# FECHAMENTO
# =============================
cursor.close()
conn.close()
print("Todas as versões foram processadas com sucesso!")
