import json
import pymysql

# Configurações do banco de dados
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""  # Banco sem senha
DB_NAME = "biblia_db"
JSON_FILE = "nvi.json"  # Nome correto do JSON
VERSION_CODE = "nvi"
VERSION_NAME = "NVI"

def main():
    # Conecta ao banco
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        autocommit=True
    )
    cursor = conn.cursor()

    # Cria a versão se não existir
    cursor.execute("SELECT id FROM versions WHERE version_code=%s", (VERSION_CODE,))
    version = cursor.fetchone()
    if version:
        version_id = version[0]
    else:
        cursor.execute(
            "INSERT INTO versions (name, version_code) VALUES (%s, %s)",
            (VERSION_NAME, VERSION_CODE)
        )
        version_id = cursor.lastrowid

    # Lê o JSON
    with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
        books_data = json.load(f)

    # Verifica se é lista de livros ou apenas um livro
    if isinstance(books_data, dict):
        books_data = [books_data]

    book_order_counter = 1
    for book in books_data:
        abbrev = book.get("abbrev")
        name = book.get("name", abbrev)  # Se não tiver name, usa a sigla
        chapters = book.get("chapters", [])

        # Evita duplicar livros
        cursor.execute("SELECT id FROM books WHERE abbrev=%s AND version_id=%s", (abbrev, version_id))
        if cursor.fetchone():
            print(f"Livro {name} já existe, pulando...")
            book_order_counter += 1
            continue

        try:
            cursor.execute(
                "INSERT INTO books (version_id, name, abbrev, book_order) VALUES (%s, %s, %s, %s)",
                (version_id, name, abbrev, book_order_counter)
            )
            book_id = cursor.lastrowid
            print(f"Criado livro: {abbrev} - {name}")
        except Exception as e:
            print(f"Erro ao criar book: {abbrev} {e}")
            book_order_counter += 1
            continue

        # Insere capítulos e versículos
        chapter_number = 1
        for chapter in chapters:
            if not isinstance(chapter, list):
                print(f"Capítulo inválido em {abbrev}: {chapter}")
                continue
            try:
                cursor.execute(
                    "INSERT INTO chapters (book_id, chapter_number) VALUES (%s, %s)",
                    (book_id, chapter_number)
                )
                chapter_id = cursor.lastrowid
            except Exception as e:
                print(f"Erro ao criar capítulo {chapter_number} do livro {abbrev}: {e}")
                chapter_number += 1
                continue

            verse_number = 1
            for verse in chapter:
                try:
                    cursor.execute(
                        "INSERT INTO verses (chapter_id, verse_number, text) VALUES (%s, %s, %s)",
                        (chapter_id, verse_number, verse)
                    )
                    verse_number += 1
                except Exception as e:
                    print(f"Erro ao criar versículo {verse_number} do capítulo {chapter_number} do livro {abbrev}: {e}")
            chapter_number += 1

        book_order_counter += 1

    cursor.close()
    conn.close()
    print("Importação concluída.")

if __name__ == "__main__":
    main()
