"""
고해상도 차량 이미지 크롤링 - 엔카에서 직접 검색
"""
import asyncio
import httpx
from pathlib import Path
from playwright.async_api import async_playwright

SAVE_DIR = Path("/home/jjh0709/Project_2026_1/backend/app/static/images/cars")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

CARS = [
    {"id": 1, "brand": "현대", "model": "NF소나타", "filename": "nf_sonata.jpg"},
    {"id": 2, "brand": "현대", "model": "그랜저", "filename": "grandeur.jpg"},
    {"id": 3, "brand": "기아", "model": "K5", "filename": "k5.jpg"},
    {"id": 4, "brand": "기아", "model": "쏘렌토", "filename": "sorento.jpg"},
    {"id": 5, "brand": "제네시스", "model": "G80", "filename": "g80.jpg"},
    {"id": 6, "brand": "BMW", "model": "520i", "filename": "bmw520i.jpg"},
    {"id": 7, "brand": "현대", "model": "투싼", "filename": "tucson.jpg"},
    {"id": 8, "brand": "기아", "model": "EV6", "filename": "ev6.jpg"},
    {"id": 9, "brand": "현대", "model": "아반떼", "filename": "avante.jpg"},
    {"id": 10, "brand": "쉐보레", "model": "트레일블레이저", "filename": "trailblazer.jpg"},
    {"id": 11, "brand": "현대", "model": "캐스퍼", "filename": "casper.jpg"},
    {"id": 12, "brand": "기아", "model": "카니발", "filename": "carnival.jpg"},
]


async def download_image(url: str, filepath: Path) -> bool:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            })
            if resp.status_code == 200 and len(resp.content) > 15000:
                filepath.write_bytes(resp.content)
                return True
    except:
        pass
    return False


async def search_encar_detail(page, brand: str, model: str) -> list[str]:
    """엔카 상세 페이지에서 고해상도 이미지 수집"""
    urls = []
    try:
        # 엔카 검색 API 활용
        search_url = f"http://www.encar.com/dc/dc_carsearchlist.do?carType=kor&searchType=model&q={brand}+{model}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)

        # 모든 이미지 태그에서 큰 이미지 찾기
        images = await page.query_selector_all("img")
        for img in images[:30]:
            src = await img.get_attribute("src") or ""
            data_src = await img.get_attribute("data-src") or ""
            for s in [src, data_src]:
                if s and ("ci.encar.com" in s or "encar" in s) and ("thumb" in s or "photo" in s or "img" in s):
                    # 큰 사이즈로 변환
                    s = s.replace("/thumb/", "/original/").replace("_s.", "_l.").replace("_t.", "_l.")
                    if s.startswith("//"):
                        s = "https:" + s
                    if s not in urls:
                        urls.append(s)
    except Exception as e:
        print(f"  Encar failed: {e}")
    return urls


async def search_naver(page, brand: str, model: str) -> list[str]:
    """네이버 이미지 검색"""
    urls = []
    try:
        query = f"{brand} {model} 중고차"
        search_url = f"https://search.naver.com/search.naver?where=image&query={query}&sm=tab_opt&color=&ccl=0&nso=so%3Ar%2Ca%3Aall%2Cp%3Aall&datetype=0&startdate=0&enddate=0&imgsz=large"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)

        images = await page.query_selector_all("img._image")
        for img in images[:10]:
            src = await img.get_attribute("src") or await img.get_attribute("data-source") or ""
            if src and src.startswith("http") and len(src) > 20:
                urls.append(src)
    except Exception as e:
        print(f"  Naver failed: {e}")
    return urls


async def search_google_hq(page, brand: str, model: str) -> list[str]:
    """Google에서 중간 크기 이상 이미지"""
    urls = []
    try:
        query = f"{brand} {model} 2022 exterior photo"
        await page.goto(
            f"https://www.google.com/search?q={query}&tbm=isch&tbs=isz:m",
            wait_until="domcontentloaded", timeout=15000
        )
        await page.wait_for_timeout(2000)

        # Google 이미지의 data-src 또는 src
        images = await page.query_selector_all("img")
        for img in images[:20]:
            src = await img.get_attribute("src") or ""
            if src.startswith("http") and "google" not in src and "gstatic" not in src and len(src) > 50:
                urls.append(src)
    except Exception as e:
        print(f"  Google failed: {e}")
    return urls


async def main():
    print("=== 고해상도 차량 이미지 크롤러 ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        for car in CARS:
            filepath = SAVE_DIR / car["filename"]

            # 기존 파일이 충분히 크면 스킵
            if filepath.exists() and filepath.stat().st_size > 30000:
                print(f"[{car['id']:2d}] {car['brand']} {car['model']} → HQ 이미지 이미 존재 ({filepath.stat().st_size // 1024}KB)")
                continue

            print(f"[{car['id']:2d}] {car['brand']} {car['model']} 검색 중...")

            # 1차: 엔카 고해상도
            image_urls = await search_encar_detail(page, car["brand"], car["model"])
            print(f"  Encar: {len(image_urls)} URLs")

            # 2차: 네이버
            if len(image_urls) < 2:
                naver_urls = await search_naver(page, car["brand"], car["model"])
                image_urls.extend(naver_urls)
                print(f"  Naver: {len(naver_urls)} URLs")

            # 3차: Google
            if len(image_urls) < 2:
                google_urls = await search_google_hq(page, car["brand"], car["model"])
                image_urls.extend(google_urls)
                print(f"  Google: {len(google_urls)} URLs")

            # 다운로드 시도 (최소 15KB 이상)
            downloaded = False
            for url in image_urls:
                if await download_image(url, filepath):
                    size_kb = filepath.stat().st_size // 1024
                    print(f"  ✓ {car['filename']} ({size_kb}KB)")
                    downloaded = True
                    break

            if not downloaded:
                print(f"  ✗ 고해상도 이미지 못 찾음 (기존 유지)")

            await page.wait_for_timeout(1500)

        await browser.close()

    print(f"\n=== 최종 결과 ===")
    for car in CARS:
        filepath = SAVE_DIR / car["filename"]
        if filepath.exists():
            size = filepath.stat().st_size
            quality = "HQ" if size > 30000 else "LQ"
            print(f"  [{quality}] {car['filename']:20s} {size // 1024:>4d}KB")
        else:
            print(f"  [--] {car['filename']:20s}    없음")


if __name__ == "__main__":
    asyncio.run(main())
