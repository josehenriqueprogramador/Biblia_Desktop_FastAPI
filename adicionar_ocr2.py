from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import os
import enviar_leitura_telegram

router = APIRouter()

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

@router.post("/upload_e_processar")
async def upload_e_processar(file: UploadFile = File(...)):
    """
    Recebe uma imagem, salva no diretório uploads/
    e aciona o processamento COMPLETO já existente
    no arquivo enviar_leitura_telegram.py
    """
    try:
        filename = os.path.basename(file.filename)
        file_path = UPLOADS_DIR / filename

        # salva o arquivo
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # roda o fluxo COMPLETO já existente
        enviar_leitura_telegram.main()

        return {
            "status": "ok",
            "arquivo_recebido": str(file_path),
            "mensagem": "Processamento acionado."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

