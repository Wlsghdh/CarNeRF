"""
차량 썸네일 이미지 크롤링 스크립트
- 각 차량 모델별로 적합한 이미지를 엔카/KB차차차에서 수집
- Playwright (headless chromium) 사용
"""
import asyncio
import os
import hashlib
import httpx
from pathlib import Path
from playwright.async_api import async_playwright

SAVE_DIR = Path("/home/jjh0709/Project_2026_1/backend/app/static/images/cars")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# seed_data.py 기반 차량 목록
CARS = [
    {"id": 1, "query": "현대 NF소나타 2008 실버", "filename": "nf_sonata.jpg"},
    {"id": 2, "query": "현대 그랜저 2022 화이트 르블랑", "filename": "grandeur.jpg"},
    {"id": 3, "query": "기아 K5 2021 그레이", "filename": "k5.jpg"},
    {"id": 4, "query": "기아 쏘렌토 2023 블랙", "filename": "sorento.jpg"},
    {"id": 5, "query": "제네시스 G80 2021 블루", "filename": "g80.jpg"},
    {"id": 6, "query": "BMW 520i 2020 화이트", "filename": "bmw520i.jpg"},
    {"id": 7, "query": "현대 투싼 2023 하이브리드", "filename": "tucson.jpg"},
    {"id": 8, "query": "기아 EV6 2022 화이트", "filename": "ev6.jpg"},
    {"id": 9, "query": "현대 아반떼 2024 레드", "filename": "avante.jpg"},
    {"id": 10, "query": "쉐보레 트레일블레이저 2022 블루", "filename": "trailblazer.jpg"},
    {"id": 11, "query": "현대 캐스퍼 2023 오렌지", "filename": "casper.jpg"},
    {"id": 12, "query": "기아 카니발 2021 블랙", "filename": "carnival.jpg"},
]


async def download_image(url: str, filepath: Path) -> bool:
    """이미지 다운로드"""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Referer": "https://www.google.com/",
            })
            if resp.status_code == 200 and len(resp.content) > 5000:
                filepath.write_bytes(resp.content)
                return True
    except Exception as e:
        print(f"  Download failed: {e}")
    return False


async def search_encar(page, query: str) -> list[str]:
    """엔카에서 차량 이미지 URL 검색"""
    urls = []
    try:
        search_url = f"http://www.encar.com/dc/dc_carsearchlist.do?carType=kor&searchType=model&q={query}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)

        # 차량 카드의 이미지 추출
        images = await page.query_selector_all("img.thumb")
        for img in images[:5]:
            src = await img.get_attribute("src")
            if src and ("ci.encar.com" in src or "img" in src):
                if src.startswith("//"):
                    src = "https:" + src
                urls.append(src)
    except Exception as e:
        print(f"  Encar search failed: {e}")
    return urls


async def search_kbchachacha(page, query: str) -> list[str]:
    """KB차차차에서 차량 이미지 URL 검색"""
    urls = []
    try:
        parts = query.split()
        brand = parts[0] if parts else ""
        model = parts[1] if len(parts) > 1 else ""
        search_url = f"https://www.kbchachacha.com/public/search/main.kbc#!?saleStatus=Y&_pageSize=10&_pageNo=1&_orderBy=S11&carName={brand}+{model}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(3000)

        images = await page.query_selector_all(".listCont img, .carBox img, .pic img")
        for img in images[:5]:
            src = await img.get_attribute("src") or await img.get_attribute("data-src")
            if src and len(src) > 10:
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = "https://www.kbchachacha.com" + src
                urls.append(src)
    except Exception as e:
        print(f"  KB search failed: {e}")
    return urls


async def search_google_images(page, query: str) -> list[str]:
    """Google 이미지 검색 (fallback)"""
    urls = []
    try:
        search_url = f"https://www.google.com/search?q={query}+자동차+중고차&tbm=isch&tbs=isz:m"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)

        images = await page.query_selector_all("img[src*='http']")
        for img in images[:10]:
            src = await img.get_attribute("src")
            if src and src.startswith("http") and "google" not in src and len(src) > 20:
                urls.append(src)
    except Exception as e:
        print(f"  Google search failed: {e}")
    return urls


async def main():
    print("=== CarNeRF 차량 이미지 크롤러 ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        for car in CARS:
            filepath = SAVE_DIR / car["filename"]

            # 이미 다운로드됨
            if filepath.exists() and filepath.stat().st_size > 5000:
                print(f"[{car['id']:2d}] {car['query']} → 이미 존재 ({filepath.stat().st_size // 1024}KB)")
                continue

            print(f"[{car['id']:2d}] {car['query']} 검색 중...")

            # 1차: 엔카
            image_urls = await search_encar(page, car["query"])
            # 2차: KB차차차
            if not image_urls:
                image_urls = await search_kbchachacha(page, car["query"])
            # 3차: Google
            if not image_urls:
                image_urls = await search_google_images(page, car["query"])

            # 다운로드 시도
            downloaded = False
            for url in image_urls:
                if await download_image(url, filepath):
                    size_kb = filepath.stat().st_size // 1024
                    print(f"  ✓ 다운로드 완료: {car['filename']} ({size_kb}KB)")
                    downloaded = True
                    break

            if not downloaded:
                print(f"  ✗ 이미지를 찾지 못했습니다")

            await page.wait_for_timeout(1000)  # rate limit

        await browser.close()

    # 결과 요약
    print(f"\n=== 결과 ===")
    for car in CARS:
        filepath = SAVE_DIR / car["filename"]
        if filepath.exists():
            print(f"  ✓ {car['filename']} ({filepath.stat().st_size // 1024}KB)")
        else:
            print(f"  ✗ {car['filename']} (없음)")


if __name__ == "__main__":
    asyncio.run(main())
