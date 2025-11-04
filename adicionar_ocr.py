from fastapi import FastAPI
from pathlib import Path
from PIL import Image
import pytesseract
import json
import datetime
import enviar_leitura_whatsapp

# Evita criar outro app se já existir
try:
    app
except NameError:
    app = FastAPI()

@app.get("/processar_ocr")
def processar_ocr():
    uploads_dir = Path("uploads")
    processadas_dir = uploads_dir / "processadas"
    processadas_dir.mkdir(exist_ok=True)

    mensagens = []
    for img_path in uploads_dir.glob("*.*"):
        if (processadas_dir / img_path.name).exists():
            continue  # já processada

        try:
            texto = pytesseract.image_to_string(Image.open(img_path), lang="por")
            
            # salva no JSON de leituras
            enviar_leitura_whatsapp.garantir_estrutura()
            with open(enviar_leitura_whatsapp.LEITURAS_JSON, "r+", encoding="utf-8") as f:
                leituras = json.load(f)
                leituras.append({"data_envio": str(datetime.date.today()), "texto": texto})
                f.seek(0)
                json.dump(leituras, f, ensure_ascii=False, indent=2)
                f.truncate()

            mensagens.append(f"✅ {img_path.name} processada com sucesso!")
            img_path.rename(processadas_dir / img_path.name)
        except Exception as e:
            mensagens.append(f"❌ Erro em {img_path.name}: {e}")

    return {"mensagens": mensagens}
