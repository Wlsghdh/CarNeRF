"""retriever 동작 검증 — 인덱싱 후 바로 실행해서 결과 품질 확인.

사용:
  conda activate rag
  python scripts/rag/test_retrieve.py
  python scripts/rag/test_retrieve.py --brand 현대 --model 그랜저 --k 5
"""
import argparse
import sys
from pathlib import Path

# backend/app가 import 가능하도록 sys.path 조정
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--query", default="")
    parser.add_argument("--k", type=int, default=3)
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

    # 디폴트: 시드 차종 12개 골든 테스트
    targets = [
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
    print(f"=== 골든 테스트: 12 시드 차종 (top {args.k} each) ===\n")
    for brand, model in targets:
        chunks = retrieve(brand, model, k=args.k)
        if chunks:
            print(f"✓ {brand}/{model}: {len(chunks)}건 (top score={chunks[0].score:.3f})")
            print(f"   └ {chunks[0].title[:60]}")
        else:
            print(f"✗ {brand}/{model}: 0건")


if __name__ == "__main__":
    main()
