"""Chroma 클라이언트 + BGE-M3 임베더 싱글톤.

서버 프로세스 내에서 한 번만 로드되도록 lru_cache 사용.
모델 첫 로드 ~5초, 첫 다운로드는 ~2.3GB.
"""
from functools import lru_cache
from pathlib import Path

# 프로젝트 루트: backend/app/rag/chroma_client.py → 4단계 위
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHROMA_DIR = PROJECT_ROOT / "data" / "rag" / "chroma"
COLLECTION_NAME = "car_reviews"
EMBED_MODEL = "BAAI/bge-m3"


@lru_cache(maxsize=1)
def get_client():
    import chromadb

    return chromadb.PersistentClient(path=str(CHROMA_DIR))


@lru_cache(maxsize=1)
def get_collection():
    return get_client().get_collection(COLLECTION_NAME)


DEFECT_COLLECTION_NAME = "defect_explanations"


@lru_cache(maxsize=1)
def get_defect_collection():
    """결함/검수 가이드 corpus (별도 collection)."""
    return get_client().get_collection(DEFECT_COLLECTION_NAME)


@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def chroma_ready() -> bool:
    """Chroma 컬렉션이 적재되어있는지 확인 (FastAPI startup 점검용)."""
    try:
        return get_collection().count() > 0
    except Exception:
        return False
