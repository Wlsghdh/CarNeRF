"""retriever 동작 검증 — 인덱싱 후 바로 실행해서 결과 품질 확인.

사용:
  conda activate rag
  python scripts/rag/test_retrieve.py                       # 골든 테스트 + 메트릭
  python scripts/rag/test_retrieve.py --metrics-only        # 메트릭만 (발표자료용)
  python scripts/rag/test_retrieve.py --brand 현대 --model 그랜저 --k 5
"""
import argparse
import sys
from pathlib import Path

# backend/app가 import 가능하도록 sys.path 조정
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


# 골든 셋: 시드 12개 차종. 각 쿼리는 retrieve()의 자동 쿼리에 의존하지 않고
# 사용자가 실제로 입력할 만한 자연어로 정의. (brand, model)이 top-5에 들어오는지 확인.
GOLDEN_TARGETS = [
    ("현대", "그랜저"),
    ("현대", "투싼"),
    ("현대", "아반떼"),
    ("현대", "캐스퍼"),
    ("현대", "NF소나타"),
    ("기아", "K5"),
    ("기아", "쏘렌토"),
    ("기아", "EV6"),
    ("기아", "카니발"),
    ("제네시스", "G80"),
    ("BMW", "520i"),
    ("쉐보레", "트레일블레이저"),
]


def _run_golden_metrics(k: int = 5) -> dict:
    """retrieve()로 각 차종 검색 → (brand,model) 메타가 일치한 청크가 1건 이상이면 hit.

    Top-K 정확도 = hit 개수 / 전체. retrieve()는 이미 brand+model 메타필터를
    걸므로, hit률이 곧 "해당 차종 corpus 청크 1건 이상 검색 성공" 비율.
    """
    from app.rag.retriever import retrieve

    hits = 0
    rows: list[tuple[str, str, bool, float]] = []
    for brand, model in GOLDEN_TARGETS:
        chunks = retrieve(brand, model, k=k)
        hit = bool(chunks)
        top = chunks[0].score if chunks else 0.0
        if hit:
            hits += 1
        rows.append((brand, model, hit, top))

    total = len(GOLDEN_TARGETS)
    return {
        "k": k,
        "total": total,
        "hits": hits,
        "accuracy": round(hits / total * 100, 1),
        "rows": rows,
    }


def _print_metrics_report(m: dict) -> None:
    print("\n" + "═" * 56)
    print(f"  RAG TOP-{m['k']} 정확도: {m['hits']}/{m['total']} = {m['accuracy']}%")
    print("═" * 56)
    print("  (시드 차종 골든셋: 12종 · BGE-M3 임베딩 · ChromaDB cosine)")
    print("─" * 56)
    for brand, model, hit, top in m["rows"]:
        mark = "✓" if hit else "✗"
        sc = f"score {top:.3f}" if hit else "no match"
        print(f"  {mark}  {brand:>6} / {model:<14}  {sc}")
    print("═" * 56 + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--query", default="")
    parser.add_argument("--k", type=int, default=5,
                        help="top-K (메트릭 모드 기본 5)")
    parser.add_argument("--metrics-only", action="store_true",
                        help="발표자료용 한 줄 메트릭만 출력")
    args = parser.parse_args()

    from app.rag.retriever import retrieve

    # 단일 조회 모드
    if args.brand and args.model:
        chunks = retrieve(args.brand, args.model, args.query, args.k)
        print(f"\n=== {args.brand} {args.model} (top {args.k}) ===")
        for i, c in enumerate(chunks, 1):
            print(f"\n[{i}] score={c.score:.3f}  source={c.source}")
            print(f"  title: {c.title[:70]}")
            print(f"  text : {c.text[:200]}...")
        if not chunks:
            print("  (no results)")
        return

    # 디폴트: 골든 테스트 + Top-K 메트릭
    if args.metrics_only:
        m = _run_golden_metrics(k=args.k)
        print(f"Top-{m['k']} 정확도: {m['accuracy']}% ({m['hits']}/{m['total']})")
        return

    print(f"=== 골든 테스트: {len(GOLDEN_TARGETS)} 시드 차종 (top {args.k} each) ===\n")
    for brand, model in GOLDEN_TARGETS:
        chunks = retrieve(brand, model, k=args.k)
        if chunks:
            print(f"✓ {brand}/{model}: {len(chunks)}건 (top score={chunks[0].score:.3f})")
            print(f"   └ {chunks[0].title[:60]}")
        else:
            print(f"✗ {brand}/{model}: 0건")

    m = _run_golden_metrics(k=args.k)
    _print_metrics_report(m)


if __name__ == "__main__":
    main()
