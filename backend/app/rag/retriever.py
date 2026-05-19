"""차종별 리뷰 청크 retrieval — ai_summary.py에서 import해서 사용.

전략:
  1) brand AND model 메타필터 + 시맨틱 검색 (strict)
  2) 결과 없으면 model 만 (loose)
  3) 그래도 없으면 빈 리스트

쿼리는 user-supplied 또는 자동 생성 ("{brand} {model} 장단점 시승 고질병").
"""
import os
from dataclasses import dataclass, asdict
from typing import Optional

from .chroma_client import get_collection, get_embedder


# cosine similarity 컷오프. BGE-M3 normalized 기준 0.3 미만은 사실상 무관.
# 환경변수 RAG_SIM_THRESHOLD로 조정 (e.g. 시연 직전 0.4로 보수적 조정 가능).
_DEFAULT_THRESHOLD = 0.30


def _sim_threshold(override: Optional[float] = None) -> float:
    if override is not None:
        return override
    try:
        return float(os.getenv("RAG_SIM_THRESHOLD", _DEFAULT_THRESHOLD))
    except ValueError:
        return _DEFAULT_THRESHOLD


@dataclass
class Chunk:
    text: str
    url: str
    title: str
    source: str
    brand: str
    model: str
    score: float  # cosine similarity (1.0 - distance)

    def to_dict(self) -> dict:
        return asdict(self)


def _query_with_where(q_emb: list[float], k: int, where: Optional[dict]) -> dict:
    coll = get_collection()
    kwargs: dict = {"query_embeddings": [q_emb], "n_results": k}
    if where:
        kwargs["where"] = where
    return coll.query(**kwargs)


def retrieve(
    brand: str,
    model: str,
    query: str = "",
    k: int = 5,
    min_score: Optional[float] = None,
) -> list[Chunk]:
    """차량 (brand, model)에 대한 top-k 리뷰 청크.

    Args:
        brand: 예 "현대"
        model: 예 "그랜저" (시드 DB의 표기와 일치해야 함)
        query: 자연어 질의. 비어있으면 자동 생성.
        k: 반환 개수
        min_score: cosine similarity 컷오프. 미만 청크 제외.

    Returns:
        Chunk 리스트 (similarity score 내림차순). 매치 없거나 임계값 미만이면 [].
    """
    if not query:
        query = f"{brand} {model} 장단점 시승 주행감 고질병"

    threshold = _sim_threshold(min_score)

    embedder = get_embedder()
    q_emb = embedder.encode(
        [query], normalize_embeddings=True, convert_to_numpy=True
    )[0].tolist()

    # 1) Strict: brand AND model
    result = _query_with_where(
        q_emb, k, where={"$and": [{"brand": brand}, {"model": model}]}
    )
    if not result["ids"] or not result["ids"][0]:
        # 2) Loose: model only
        result = _query_with_where(q_emb, k, where={"model": model})

    if not result["ids"] or not result["ids"][0]:
        return []

    chunks: list[Chunk] = []
    docs = result["documents"][0]
    metas = result["metadatas"][0]
    dists = result["distances"][0]
    for doc, meta, dist in zip(docs, metas, dists):
        score = round(1.0 - float(dist), 4)
        if score < threshold:
            continue
        chunks.append(
            Chunk(
                text=doc,
                url=meta.get("url", ""),
                title=meta.get("title", ""),
                source=meta.get("source", ""),
                brand=meta.get("brand", ""),
                model=meta.get("model", ""),
                score=score,
            )
        )
    return chunks


def get_sources(chunks: list[Chunk]) -> list[dict]:
    """청크 리스트에서 고유 출처(url, title, source) 추출."""
    seen = set()
    sources = []
    for c in chunks:
        if c.url in seen:
            continue
        seen.add(c.url)
        sources.append({"url": c.url, "title": c.title, "source": c.source})
    return sources


@dataclass
class VehicleMatch:
    brand: str
    model: str
    score: float
    excerpt: str
    excerpt_url: str
    excerpt_title: str
    excerpt_source: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DefectExplanation:
    """결함 풀이용 RAG 결과 청크."""
    text: str
    url: str
    title: str
    source: str
    category: str   # inspection / accident / repair / terminology / flood / corrosion
    topic: str      # paint / dpf / general 등
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


def retrieve_defect_explanations(
    defect_type_kr: str,
    severity: str = "",
    k: int = 3,
) -> list[DefectExplanation]:
    """결함 종류·심각도 → 일반인용 풀이 청크 검색.

    검색 쿼리: '{결함종류} {심각도} 수리 비용 검수 설명'.
    카테고리: inspection / repair / accident.
    """
    from .chroma_client import get_defect_collection, get_embedder

    parts = [defect_type_kr]
    if severity:
        parts.append(severity)
    parts.extend(["수리 비용", "검수", "외관"])
    query = " ".join(parts)

    try:
        coll = get_defect_collection()
    except Exception:
        return []

    embedder = get_embedder()
    q_emb = embedder.encode(
        [query], normalize_embeddings=True, convert_to_numpy=True
    )[0].tolist()

    try:
        result = coll.query(
            query_embeddings=[q_emb],
            n_results=k,
            where={"brand": {"$in": ["inspection", "repair", "accident"]}},
        )
    except Exception:
        return []

    if not result["ids"] or not result["ids"][0]:
        return []

    # 결함 풀이는 매칭 어휘가 좁아 임계값을 더 낮게 (default 0.2)
    threshold = float(os.getenv("RAG_DEFECT_SIM_THRESHOLD", "0.20"))
    out: list[DefectExplanation] = []
    for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        score = round(1.0 - float(dist), 4)
        if score < threshold:
            continue
        out.append(DefectExplanation(
            text=doc, url=meta.get("url", ""), title=meta.get("title", ""),
            source=meta.get("source", ""), category=meta.get("brand", ""),
            topic=meta.get("model", ""), score=score,
        ))
    return out


def retrieve_terminology(term_kr: str, k: int = 2) -> list[DefectExplanation]:
    """차량 용어(예: DPF, CVT, 서스펜션) 풀이 청크."""
    from .chroma_client import get_defect_collection, get_embedder
    query = f"{term_kr} 자동차 설명 정비 일반인"
    try:
        coll = get_defect_collection()
    except Exception:
        return []
    embedder = get_embedder()
    q_emb = embedder.encode(
        [query], normalize_embeddings=True, convert_to_numpy=True
    )[0].tolist()
    try:
        result = coll.query(
            query_embeddings=[q_emb],
            n_results=k,
            where={"brand": "terminology"},
        )
    except Exception:
        return []
    if not result["ids"] or not result["ids"][0]:
        return []
    threshold = float(os.getenv("RAG_DEFECT_SIM_THRESHOLD", "0.20"))
    out: list[DefectExplanation] = []
    for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        score = round(1.0 - float(dist), 4)
        if score < threshold:
            continue
        out.append(DefectExplanation(
            text=doc, url=meta.get("url", ""), title=meta.get("title", ""),
            source=meta.get("source", ""), category=meta.get("brand", ""),
            topic=meta.get("model", ""), score=score,
        ))
    return out


def semantic_search_vehicles(
    query: str,
    top_k_chunks: int = 30,
    max_vehicles: int = 12,
    min_score: Optional[float] = None,
) -> list[VehicleMatch]:
    """자연어 쿼리 → 매칭되는 차종(brand+model) 후보 반환.

    필터 없이 전체 chunks 검색 후 차종별로 그룹화. 차종당 best chunk 1건 유지.

    Args:
        query: "조용한 패밀리 SUV" 같은 자연어
        top_k_chunks: Chroma에서 가져올 raw chunk 개수
        max_vehicles: 반환할 차종 최대 개수
        min_score: cosine similarity 컷오프. 미만 청크 제외.

    Returns:
        VehicleMatch 리스트 (best chunk score 내림차순). 매치 없으면 [].
    """
    if not query.strip():
        return []

    threshold = _sim_threshold(min_score)

    embedder = get_embedder()
    q_emb = embedder.encode(
        [query], normalize_embeddings=True, convert_to_numpy=True
    )[0].tolist()

    coll = get_collection()
    result = coll.query(query_embeddings=[q_emb], n_results=top_k_chunks)
    if not result["ids"] or not result["ids"][0]:
        return []

    docs = result["documents"][0]
    metas = result["metadatas"][0]
    dists = result["distances"][0]

    by_key: dict[tuple[str, str], dict] = {}
    for doc, meta, dist in zip(docs, metas, dists):
        score = round(1.0 - float(dist), 4)
        if score < threshold:
            continue
        brand = meta.get("brand", "")
        model = meta.get("model", "")
        key = (brand, model)
        if key not in by_key or score > by_key[key]["score"]:
            by_key[key] = {
                "brand": brand,
                "model": model,
                "score": score,
                "excerpt": doc,
                "excerpt_url": meta.get("url", ""),
                "excerpt_title": meta.get("title", ""),
                "excerpt_source": meta.get("source", ""),
            }

    matches = sorted(by_key.values(), key=lambda v: v["score"], reverse=True)
    return [VehicleMatch(**m) for m in matches[:max_vehicles]]
