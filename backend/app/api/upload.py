"""이미지 업로드 API - 파일 검증, 크기 제한, 썸네일 생성"""

import os
import uuid
import logging

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.config import UPLOAD_DIR
from app.dependencies import require_user
from app.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["upload"])

# 허용 확장자 및 MIME 타입
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB per image
MAX_IMAGE_COUNT = 10

# 썸네일 디렉토리
THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, "thumbnails")
os.makedirs(THUMBNAIL_DIR, exist_ok=True)


def _validate_image(file: UploadFile, content: bytes):
    """이미지 파일을 검증한다."""
    # 확장자 검증
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 이미지 형식입니다: {ext} (허용: {', '.join(ALLOWED_IMAGE_EXTENSIONS)})"
        )

    # MIME 타입 검증
    if file.content_type and file.content_type not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 MIME 타입입니다: {file.content_type}"
        )

    # 파일 크기 검증
    if len(content) > MAX_IMAGE_SIZE:
        size_mb = len(content) / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"이미지 크기가 너무 큽니다: {size_mb:.1f}MB (최대: {MAX_IMAGE_SIZE // (1024 * 1024)}MB)"
        )

    # 매직 바이트 검증 (파일 헤더)
    if content[:2] == b'\xff\xd8':
        return ext  # JPEG
    elif content[:8] == b'\x89PNG\r\n\x1a\n':
        return ext  # PNG
    elif content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return ext  # WebP
    else:
        raise HTTPException(
            status_code=400,
            detail="파일 내용이 이미지 형식과 일치하지 않습니다."
        )


def _create_thumbnail(content: bytes, filename: str, max_size: int = 400) -> str:
    """썸네일을 생성한다."""
    try:
        import cv2
        import numpy as np

        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        h, w = img.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        thumb_filename = f"thumb_{filename}"
        thumb_path = os.path.join(THUMBNAIL_DIR, thumb_filename)
        cv2.imwrite(thumb_path, img, [cv2.IMWRITE_JPEG_QUALITY, 80])

        return f"/uploads/thumbnails/{thumb_filename}"
    except Exception as e:
        logger.warning(f"썸네일 생성 실패: {e}")
        return None


@router.post("/images")
async def upload_images(
    files: list[UploadFile] = File(...),
    user: User = Depends(require_user),
):
    """이미지를 업로드한다. 최대 10장, 파일당 10MB."""
    if len(files) > MAX_IMAGE_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"최대 {MAX_IMAGE_COUNT}장까지 업로드 가능합니다."
        )

    saved = []
    for f in files:
        content = await f.read()

        # 검증
        _validate_image(f, content)

        # 안전한 파일명 생성
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            ext = ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(UPLOAD_DIR, filename)

        try:
            with open(path, "wb") as out:
                out.write(content)
        except OSError as e:
            logger.error(f"이미지 저장 실패: {e}")
            raise HTTPException(status_code=500, detail="이미지 저장에 실패했습니다.")

        # 썸네일 생성
        thumb_url = _create_thumbnail(content, filename)

        saved.append({
            "filename": filename,
            "url": f"/uploads/{filename}",
            "thumbnail_url": thumb_url,
            "size": len(content),
        })

    return {"files": saved, "count": len(saved)}
