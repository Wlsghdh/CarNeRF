import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File
from app.config import UPLOAD_DIR
from app.dependencies import require_user
from app.models import User

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/images")
async def upload_images(
    files: list[UploadFile] = File(...),
    user: User = Depends(require_user),
):
    saved = []
    for f in files:
        ext = os.path.splitext(f.filename)[1] or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(UPLOAD_DIR, filename)
        content = await f.read()
        with open(path, "wb") as out:
            out.write(content)
        saved.append({"filename": filename, "url": f"/uploads/{filename}"})
    return {"files": saved}
