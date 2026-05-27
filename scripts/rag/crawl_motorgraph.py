"""모터그래프 자동차 리뷰 크롤러 (RAG Phase 1).

전략:
  1) S2N4 (리뷰) 카테고리 페이지 페이지네이션 순회
  2) 각 글 fetch → meta keywords/title로 시드 차종 매칭
  3) 매칭된 글 본문 추출 → JSONL 저장
  4) 차종당 N건 채우면 종료

사용:
  conda activate rag
  python scripts/rag/crawl_motorgraph.py --per-target 5 --max-pages 30
"""
import argparse
import json
import re
import time
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

BASE = "https://www.motorgraph.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CarNeRF-RAG/0.1; research)",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 시드 DB 12 차종 매칭 키워드 (대소문자 무관)
TARGETS = [
    ("현대", "NF소나타", ["소나타"]),         # NF는 단종 → 일반 소나타로 fallback
    ("현대", "그랜저", ["그랜저"]),
    ("기아", "K5", ["k5"]),
    ("기아", "쏘렌토", ["쏘렌토"]),
    ("제네시스", "G80", ["g80"]),
    ("BMW", "520i", ["520i", "5시리즈", "5 시리즈"]),
    ("현대", "투싼", ["투싼"]),
    ("기아", "EV6", ["ev6"]),
    ("현대", "아반떼", ["아반떼"]),
    ("쉐보레", "트레일블레이저", ["트레일블레이저"]),
    ("현대", "캐스퍼", ["캐스퍼"]),
    ("기아", "카니발", ["카니발"]),
]


def fetch(client: httpx.Client, url: str) -> Optional[str]:
    try:
        r = client.get(url, timeout=15, follow_redirects=True)
        r.raise_for_status()
        return r.content.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ! fetch failed {url}: {e}")
        return None


def parse_list_page(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    for it in soup.select("li.item, div.item"):
        a = it.find("a", href=lambda x: x and "articleView.html?idxno=" in x)
        if not a:
            continue
        href = a.get("href")
        if href.startswith("/"):
            href = BASE + href
        if href not in urls:
            urls.append(href)
    return urls


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
    section = meta("article:section")
    published = meta("article:published_time")

    body_el = soup.select_one(
        ".article-view-content, .article-body, .article-veiw-body, #article-view-content-div"
    )
    body = body_el.get_text(" ", strip=True) if body_el else ""

    if not title or len(body) < 800:
        return None

    if section and section not in ("자동차", "라이프 스타일"):
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


def match_target(article: dict) -> Optional[tuple[str, str]]:
    """차종 매칭: 1) title/keywords 우선, 2) 차선으로 본문 등장 빈도(>=3).

    여러 차종이 나오면 가장 많이 등장한 차종을 선택.
    """
    title = article.get("title", "").lower()
    kw = article.get("keywords", "").lower()
    body = article.get("body", "").lower()

    # 1) title/keywords 직접 매칭 (가장 신뢰도 높음)
    for brand, model, kws in TARGETS:
        if any(k.lower() in title or k.lower() in kw for k in kws):
            return brand, model

    # 2) 본문 등장 빈도 매칭 (N >= 3)
    best = None
    best_count = 0
    for brand, model, kws in TARGETS:
        total = sum(body.count(k.lower()) for k in kws)
        if total >= 3 and total > best_count:
            best = (brand, model)
            best_count = total
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/rag/raw/motorgraph.jsonl")
    parser.add_argument("--per-target", type=int, default=5)
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--section-code", default="S2N4")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {f"{b}/{m}": 0 for b, m, _ in TARGETS}
    target_total = args.per_target * len(TARGETS)
    saved: list[dict] = []
    seen_urls: set[str] = set()
    skip_reasons = {"too_short": 0, "wrong_section": 0, "no_match": 0, "quota_full": 0}

    with httpx.Client(headers=HEADERS) as client:
        for page in range(1, args.max_pages + 1):
            list_url = (
                f"{BASE}/news/articleList.html"
                f"?sc_sub_section_code={args.section_code}&view_type=sm&page={page}"
            )
            print(f"[page {page}] {list_url}")
            html = fetch(client, list_url)
            if not html:
                continue
            urls = parse_list_page(html)
            print(f"  {len(urls)} article links")

            for url in urls:
                if sum(counts.values()) >= target_total:
                    break
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                a_html = fetch(client, url)
                if not a_html:
                    continue
                article = parse_article(a_html, url)
                if not article:
                    skip_reasons["too_short"] += 1
                    continue
                match = match_target(article)
                if not match:
                    skip_reasons["no_match"] += 1
                    continue
                brand, model = match
                key = f"{brand}/{model}"
                if counts[key] >= args.per_target:
                    skip_reasons["quota_full"] += 1
                    continue

                idxno_m = re.search(r"idxno=(\d+)", url)
                article.update(
                    {
                        "id": f"motorgraph_{idxno_m.group(1)}" if idxno_m else f"motorgraph_{len(saved)}",
                        "source": "motorgraph",
                        "brand": brand,
                        "model": model,
                    }
                )
                saved.append(article)
                counts[key] += 1
                print(
                    f"  ✓ [{key}] {article['title'][:55]} "
                    f"(body={len(article['body'])}자, {counts[key]}/{args.per_target})"
                )
                time.sleep(args.delay)

            if sum(counts.values()) >= target_total:
                print(f"\n[done] target reached at page {page}")
                break

    with out_path.open("w", encoding="utf-8") as f:
        for a in saved:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(saved)} articles → {out_path}")
    print("Per-target counts:")
    for k, c in counts.items():
        marker = "✓" if c >= args.per_target else " "
        print(f"  {marker} {k}: {c}/{args.per_target}")
    print(f"\nSkip stats: {skip_reasons}")


if __name__ == "__main__":
    main()
