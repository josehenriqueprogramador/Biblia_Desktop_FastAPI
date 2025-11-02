#!/usr/bin/env python3

import os
from pathlib import Path
from html import escape

# Caminho base
base = Path.cwd()
saida = base / "projeto.html"

# Extensões a ignorar
ignore_ext = [".json", ".pyc"]

# Diretórios a ignorar
ignore_dirs = {'.git', '__pycache__'}

# Cabeçalho HTML
html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>📘 Biblia_Desktop - Conteúdo Completo</title>
<style>
body { font-family: 'Courier New', monospace; background: #111; color: #eee; padding: 20px; }
h1 { color: #6cf; }
h2 { color: #4af; margin-top: 40px; }
pre { background: #1c1c1c; padding: 15px; border-radius: 10px; border: 1px solid #333; overflow-x: auto; }
a { color: #0af; text-decoration: none; }
a:hover { text-decoration: underline; }
ul { list-style-type: none; }
li { margin: 4px 0; }
small { color: #888; }
</style>
</head>
<body>
<h1 id="topo">📘 Projeto Biblia_Desktop</h1>
<p><small>Gerado automaticamente com estrutura de diretórios e conteúdo.</small></p>
<h2>📁 Índice</h2>
<ul>
"""

# Cria índice
for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if d not in ignore_dirs]  # Ignora pastas
    for f in files:
        file_path = Path(root) / f
        if file_path.suffix.lower() in ignore_ext:
            continue
        if file_path == saida:
            continue  # Ignora o próprio HTML gerado
        rel_path = file_path.relative_to(base)
        anchor = str(rel_path).replace("/", "_")
        html += f'<li><a href="#{anchor}">{rel_path}</a></li>\n'

html += "</ul><hr>"

# Mostra estrutura + conteúdo
for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if d not in ignore_dirs]  # Ignora pastas
    rel_dir = Path(root).relative_to(base)
    if rel_dir == Path("."):
        html += "<h2>📂 Diretório raiz</h2>"
    else:
        html += f"<h2>📂 {rel_dir}</h2>"

    if not files:
        html += "<p><small>(vazio)</small></p>"

    for f in files:
        file_path = Path(root) / f
        if file_path.suffix.lower() in ignore_ext:
            continue
        if file_path == saida:
            continue  # Ignora o próprio HTML gerado
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            content = f"[Erro ao ler o arquivo: {e}]"
        rel_path = file_path.relative_to(base)
        anchor = str(rel_path).replace("/", "_")
        html += f'<h3 id="{anchor}">📄 {rel_path}</h3>'
        html += f"<pre>{escape(content)}</pre>"

# Finaliza
html += "</body></html>"

saida.write_text(html, encoding="utf-8")
print(f"✅ Arquivo HTML completo gerado: {saida}")
