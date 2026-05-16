"""큐레이션된 URL 리스트에서 자동차 리뷰 본문 자동 추출 → JSONL.

입력: data/rag/raw/urls.txt
  형식 (한 줄에 하나, '|' 구분):
    브랜드|모델|URL
  예:
    현대|그랜저|https://www.motorgraph.com/news/articleView.html?idxno=43686
    기아|K5|https://www.autoherald.co.kr/news/articleView.html?idxno=12345
  # 또는 ; 으로 시작하는 줄은 주석 처리

출력: data/rag/raw/articles.jsonl
  필드: id, source, url, title, body, description, keywords, published_at, brand, model

사용:
  conda activate rag
  python scripts/rag/fetch_from_urls.py --in data/rag/raw/urls.txt
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CarNeRF-RAG/0.1; research)",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 매체별 본문 셀렉터 (대부분 동일 CMS 기반이라 공통 후보 사용)
BODY_SELECTORS = [
    "#article-view-content-div",
    ".article-view-content",
    ".article-body",
    ".article-veiw-body",  # motorgraph 오타지만 실제로 이렇게 쓰임
    "[itemprop='articleBody']",
    "article",
]


def detect_source(url: str) -> str:
    host = urlparse(url).netloc.lower().lstrip("www.")
    mapping = {
        "motorgraph.com": "motorgraph",
        "autoherald.co.kr": "autoherald",
        "dailycar.co.kr": "dailycar",
        "carguy.kr": "carguy",
        "motoya.co.kr": "motoya",
        "rpm9.com": "rpm9",
        "top-rider.co.kr": "toprider",
        "autopostkorea.com": "autopostkorea",
    }
    for d, name in mapping.items():
        if d in host:
            return name
    return host or "unknown"


def fetch(client: httpx.Client, url: str) -> Optional[str]:
    try:
        r = client.get(url, timeout=20, follow_redirects=True)
        r.raise_for_status()
        return r.content.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ! fetch failed: {e}")
        return None


def parse_article(html: str, url: str) -> Optional[dict]:
    soup = BeautifulSoup(html, "lxml")

    def meta(name: str, attr: str = "property") -> str:
        m = soup.find("meta", attrs={attr: name})
        return (m.get("content", "") if m else "").strip()

    title = meta("og:title")
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""

    desc = meta("og:description")
    keywords = meta("keywords", attr="name")
    published = meta("article:published_time")
    section = meta("article:section")

    body_el = None
    for sel in BODY_SELECTORS:
        body_el = soup.select_one(sel)
        if body_el:
            break
    body = body_el.get_text(" ", strip=True) if body_el else ""

    if not title:
        print(f"  ! no title")
        return None
    if len(body) < 500:
        print(f"  ! body too short ({len(body)}자)")
        return None

    return {
        "url": url,
        "title": title,
        "body": body,
        "description": desc,
        "keywords": keywords,
        "section": section,
        "published_at": published,
    }


def parse_urls_file(path: Path) -> list[tuple[str, str, str]]:
    """Parse urls.txt → [(brand, model, url), ...]."""
    items = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3:
            print(f"  ! line {lineno} malformed (need 'brand|model|url'): {line[:80]}")
            continue
        brand, model, url = parts
        if not url.startswith("http"):
            print(f"  ! line {lineno} invalid url: {url[:80]}")
            continue
        items.append((brand, model, url))
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default="data/rag/raw/urls.txt")
    parser.add_argument("--out", default="data/rag/raw/articles.jsonl")
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    inp = Path(args.inp)
    if not inp.exists():
        print(f"input file not found: {inp}")
        sys.exit(1)

    items = parse_urls_file(inp)
    if not items:
        print("no urls to fetch")
        sys.exit(1)
    print(f"Loaded {len(items)} URLs from {inp}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    saved: list[dict] = []
    failed = 0

    with httpx.Client(headers=HEADERS) as client:
        for i, (brand, model, url) in enumerate(items, 1):
            print(f"[{i}/{len(items)}] {brand}/{model}  {url}")
            html = fetch(client, url)
            if not html:
                failed += 1
                continue
            article = parse_article(html, url)
            if not article:
                failed += 1
                continue
            source = detect_source(url)
            idxno_m = re.search(r"idxno=(\d+)", url)
            article.update(
                {
                    "id": f"{source}_{idxno_m.group(1) if idxno_m else len(saved)}",
                    "source": source,
                    "brand": brand,
                    "model": model,
                }
            )
            saved.append(article)
            print(f"  ✓ saved (body={len(article['body'])}자)")
            time.sleep(args.delay)

    with out_path.open("w", encoding="utf-8") as f:
        for a in saved:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(saved)}/{len(items)} articles → {out_path}")
    if failed:
        print(f"Failed: {failed}")

    # Per-target summary
    counts: dict[str, int] = {}
    for a in saved:
        key = f"{a['brand']}/{a['model']}"
        counts[key] = counts.get(key, 0) + 1
    print("Per-target counts:")
    for k, c in sorted(counts.items()):
        print(f"  {k}: {c}")


if __name__ == "__main__":
    main()
