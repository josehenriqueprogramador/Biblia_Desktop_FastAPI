import json
import mysql.connector
import os

json_file = 'aa.json'

if not os.path.exists(json_file):
    print(f"Arquivo não encontrado: {json_file}")
    exit(1)

conn = mysql.connector.connect(
    host='127.0.0.1',
    user='root',
    password='',
    database='biblia_db'
)

# Cursor buffered para evitar "Unread result found"
cursor_select = conn.cursor(buffered=True)
cursor_insert = conn.cursor()

with open(json_file, 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

for book_data in data:
    abbrev = book_data['abbrev'].lower()

    cursor_select.execute("SELECT id FROM books WHERE abbrev=%s", (abbrev,))
    result = cursor_select.fetchone()
    if not result:
        print(f"Livro não encontrado na tabela books: {abbrev}")
        continue
    book_id = result[0]

    chapters = book_data['chapters']
    for chapter_index, verses in enumerate(chapters):
        chapter_number = chapter_index + 1
        cursor_insert.execute(
            "INSERT INTO chapters (book_id, chapter_number) VALUES (%s, %s)",
            (book_id, chapter_number)
        )
        chapter_id = cursor_insert.lastrowid

        for verse_index, verse_text in enumerate(verses):
            verse_number = verse_index + 1
            cursor_insert.execute(
                "INSERT INTO verses (chapter_id, verse_number, text) VALUES (%s, %s, %s)",
                (chapter_id, verse_number, verse_text)
            )

conn.commit()
cursor_select.close()
cursor_insert.close()
conn.close()

print("Importação concluída!")
