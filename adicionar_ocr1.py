from fastapi import APIRouter
from pathlib import Path
from PIL import Image
import pytesseract
import json
import datetime
import enviar_leitura_telegram
import os

router = APIRouter()

@router.get("/processar_ocr")
def processar_ocr():
    uploads_dir = Path("uploads")
    processadas_dir = uploads_dir / "processadas"
    processadas_dir.mkdir(exist_ok=True)

    mensagens = []

    # Garante estrutura do JSON
    enviar_leitura_telegram.garantir_estrutura()

    for img_path in uploads_dir.glob("*.*"):
        destino = processadas_dir / img_path.name

        # Ignorar arquivos já processados
        if destino.exists():
            continue

        # Aceitar somente imagens
        if img_path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
            mensagens.append(f"⚠️ Ignorado {img_path.name} (tipo não suportado)")
            continue

        try:
            # ---- OCR ----
            texto = pytesseract.image_to_string(Image.open(img_path), lang="por")

            if not texto.strip():
                mensagens.append(f"⚠️ {img_path.name}: Nenhum texto identificado.")
                img_path.rename(destino)
                continue

            # ---- Salvar no JSON ----
            with open(enviar_leitura_telegram.LEITURAS_JSON, "r+", encoding="utf-8") as f:
                try:
                    leituras = json.load(f)
                except:
                    leituras = []

                leituras.append({
                    "data_envio": str(datetime.date.today()),
                    "texto": texto.strip()
                })

                f.seek(0)
                json.dump(leituras, f, ensure_ascii=False, indent=2)
                f.truncate()

            # ---- Enviar para Telegram ----
            try:
                enviar_leitura_telegram.enviar_telegram(texto.strip())
                mensagens.append(f"📨 Enviado ao Telegram: {img_path.name}")
            except Exception as te:
                mensagens.append(f"❌ Erro ao enviar Telegram: {te}")

            # Mover imagem
            img_path.rename(destino)

        except Exception as e:
            mensagens.append(f"❌ Erro em {img_path.name}: {e}")

    return {"mensagens": mensagens}
