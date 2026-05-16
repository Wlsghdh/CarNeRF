"""articles.jsonl → 청크 → BGE-M3 임베딩 → Chroma 적재 (RAG Phase 2).

청크 전략: 500자 + 100자 overlap
임베딩: BAAI/bge-m3 (한국어 우수, 1024-dim, dense)
벡터 DB: ChromaDB PersistentClient (data/rag/chroma)
컬렉션: car_reviews

사용:
  conda activate rag
  python scripts/rag/build_index.py
"""
import argparse
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "BAAI/bge-m3"
COLLECTION_NAME = "car_reviews"


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """문자 단위 500자 청크 + 100자 overlap, 너무 짧은 꼬리 청크 제거."""
    chunks: list[str] = []
    if not text:
        return chunks
    step = chunk_size - overlap
    i = 0
    while i < len(text):
        chunk = text[i : i + chunk_size].strip()
        if len(chunk) >= 50:
            chunks.append(chunk)
        i += step
    return chunks


def load_articles(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default="data/rag/raw/articles.jsonl")
    parser.add_argument("--chroma-dir", default="data/rag/chroma")
    parser.add_argument("--collection", default=COLLECTION_NAME)
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--model", default=EMBED_MODEL)
    args = parser.parse_args()

    articles = load_articles(Path(args.inp))
    print(f"Loaded {len(articles)} articles from {args.inp}")

    # 1) 청크화
    chunks: list[dict] = []
    for art in articles:
        body = art.get("body", "")
        body_chunks = chunk_text(body, args.chunk_size, args.overlap)
        for i, text in enumerate(body_chunks):
            chunks.append(
                {
                    "id": f"{art['id']}_c{i}",
                    "text": text,
                    "metadata": {
                        "source": art["source"],
                        "url": art["url"],
                        "title": art["title"],
                        "brand": art["brand"],
                        "model": art["model"],
                        "published_at": art.get("published_at", ""),
                        "chunk_idx": i,
                        "article_id": art["id"],
                    },
                }
            )

    print(
        f"Generated {len(chunks)} chunks "
        f"(avg {len(chunks)/len(articles):.1f} chunks/article, "
        f"avg {sum(len(c['text']) for c in chunks)//len(chunks)} chars/chunk)"
    )

    # 2) 임베딩
    print(f"\nLoading embed model: {args.model}")
    print("  (first time ~2.3GB download, then cached in ~/.cache/huggingface)")
    embedder = SentenceTransformer(args.model)
    print(f"  embedding dim: {embedder.get_sentence_embedding_dimension()}")

    print(f"\nEmbedding {len(chunks)} chunks (CPU)...")
    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    print(f"  done. shape={embeddings.shape}")

    # 3) Chroma 적재
    chroma_path = Path(args.chroma_dir)
    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))

    # 재빌드: 기존 컬렉션 삭제
    try:
        client.delete_collection(args.collection)
        print(f"\nDeleted existing collection '{args.collection}'")
    except Exception:
        pass

    collection = client.create_collection(
        name=args.collection,
        metadata={"hnsw:space": "cosine", "embed_model": args.model},
    )

    # add는 한 번에 너무 크면 메모리 폭증할 수 있어 batch로
    BATCH = 100
    for s in range(0, len(chunks), BATCH):
        e = min(s + BATCH, len(chunks))
        collection.add(
            ids=[chunks[i]["id"] for i in range(s, e)],
            documents=[chunks[i]["text"] for i in range(s, e)],
            metadatas=[chunks[i]["metadata"] for i in range(s, e)],
            embeddings=embeddings[s:e].tolist(),
        )

    print(f"\n✓ Saved {collection.count()} chunks to Chroma collection '{args.collection}'")
    print(f"  Chroma path: {chroma_path.resolve()}")

    # 차종별 분포
    from collections import Counter
    car_counts = Counter(c["metadata"]["model"] for c in chunks)
    print(f"\nChunks per model:")
    for m, n in sorted(car_counts.items()):
        print(f"  {m}: {n}")


if __name__ == "__main__":
    main()
