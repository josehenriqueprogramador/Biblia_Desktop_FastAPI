import json
import mysql.connector

# CONFIGURAÇÃO DO BANCO
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="biblia_db"
)

cursor = db.cursor()

# ID da versão inserida antes
VERSION_ID = 1

# CARREGAR O JSON
with open("nvi.json", "r", encoding="utf-8-sig") as f:
    data = json.load(f)

for book in data:
    abbrev = book["abbrev"]
    chapters = book["chapters"]

    # 1) INSERIR LIVRO (books)
    cursor.execute("""
        INSERT INTO books (abbrev)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id);
    """, (abbrev,))
    book_id = cursor.lastrowid

    # 2) INSERIR CAPÍTULOS (chapters)
    for chapter_number, verses_list in enumerate(chapters, start=1):
        
        cursor.execute("""
            INSERT INTO chapters (version_id, book_id, chapter_number)
            VALUES (%s, %s, %s)
        """, (VERSION_ID, book_id, chapter_number))

        chapter_id = cursor.lastrowid

        # 3) INSERIR VERSOS (verses)
        for verse_number, verse_text in enumerate(verses_list, start=1):
            cursor.execute("""
                INSERT INTO verses (chapter_id, verse_number, text)
                VALUES (%s, %s, %s)
            """, (chapter_id, verse_number, verse_text))

db.commit()
cursor.close()
db.close()

print("Importação concluída com sucesso!")
