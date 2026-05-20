"""
최종 차량 이미지 크롤링 - 정비된 접근법
엔카 실제 차량 사진 페이지에서 이미지 수집
"""
import asyncio
import httpx
from pathlib import Path
from playwright.async_api import async_playwright

SAVE_DIR = Path("/home/jjh0709/Project_2026_1/backend/app/static/images/cars")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

CARS = [
    {"id": 1, "query": "NF소나타", "filename": "nf_sonata.jpg", "min_h": 200},
    {"id": 2, "query": "그랜저 IG", "filename": "grandeur.jpg", "min_h": 200},
    {"id": 3, "query": "K5 DL3", "filename": "k5.jpg", "min_h": 200},
    {"id": 4, "query": "쏘렌토 MQ4", "filename": "sorento.jpg", "min_h": 200},
    {"id": 5, "query": "제네시스 G80", "filename": "g80.jpg", "min_h": 200},
    {"id": 6, "query": "BMW 5시리즈", "filename": "bmw520i.jpg", "min_h": 200},
    {"id": 7, "query": "투싼 NX4", "filename": "tucson.jpg", "min_h": 200},
    {"id": 8, "query": "EV6", "filename": "ev6.jpg", "min_h": 200},
    {"id": 9, "query": "아반떼 CN7", "filename": "avante.jpg", "min_h": 200},
    {"id": 10, "query": "트레일블레이저", "filename": "trailblazer.jpg", "min_h": 200},
    {"id": 11, "query": "캐스퍼", "filename": "casper.jpg", "min_h": 200},
    {"id": 12, "query": "카니발 KA4", "filename": "carnival.jpg", "min_h": 200},
]


async def download_and_verify(url: str, filepath: Path, min_h: int = 200) -> bool:
    """이미지 다운로드 후 크기 검증"""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "image/*,*/*",
            })
            if resp.status_code != 200:
                return False
            data = resp.content
            if len(data) < 10000:
                return False

            # 임시 파일에 저장 후 검증
            tmp = filepath.with_suffix('.tmp')
            tmp.write_bytes(data)

            from PIL import Image
            img = Image.open(tmp)
            w, h = img.size

            if h < min_h or w < 200:
                tmp.unlink()
                return False

            # Resize to reasonable web size (max 800px width)
            if w > 800:
                ratio = 800 / w
                img = img.resize((800, int(h * ratio)), Image.LANCZOS)

            img.save(filepath, "JPEG", quality=85, optimize=True)
            tmp.unlink(missing_ok=True)
            return True
    except Exception as e:
        filepath.with_suffix('.tmp').unlink(missing_ok=True)
        return False


async def crawl_encar_listing(page, query: str) -> list[str]:
    """엔카 개별 매물 페이지에서 실제 차량 사진 수집"""
    urls = []
    try:
        search_url = f"http://www.encar.com/dc/dc_carsearchlist.do?carType=kor&searchType=model&q={query}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)

        # 첫 번째 매물 링크 클릭
        links = await page.query_selector_all("a[href*='carid']")
        detail_url = None
        for link in links[:5]:
            href = await link.get_attribute("href")
            if href and "carid" in href:
                if href.startswith("/"):
                    href = "http://www.encar.com" + href
                detail_url = href
                break

        if detail_url:
            await page.goto(detail_url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)

            # 상세 페이지의 큰 이미지
            images = await page.query_selector_all("img")
            for img in images[:30]:
                src = await img.get_attribute("src") or ""
                if "ci.encar.com" in src and ("photo" in src or "carpicture" in src):
                    src = src.replace("_s.", "_l.").replace("_t.", "_l.")
                    if src.startswith("//"):
                        src = "https:" + src
                    urls.append(src)

        # 리스트 페이지의 이미지도 수집 (fallback)
        if not urls:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)
            images = await page.query_selector_all("img[src*='ci.encar.com']")
            for img in images[:10]:
                src = await img.get_attribute("src") or ""
                if src:
                    src = src.replace("_s.", "_l.").replace("_t.", "_l.").replace("/thumb/", "/original/")
                    if src.startswith("//"):
                        src = "https:" + src
                    urls.append(src)

    except Exception as e:
        print(f"  Encar error: {e}")
    return urls


async def crawl_kbchacha(page, query: str) -> list[str]:
    """KB차차차에서 차량 이미지"""
    urls = []
    try:
        search_url = f"https://www.kbchachacha.com/public/search/main.kbc#!?saleStatus=Y&carName={query}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(4000)

        images = await page.query_selector_all("img")
        for img in images[:30]:
            src = await img.get_attribute("src") or await img.get_attribute("data-src") or ""
            if src and ("kbchachacha" in src or "kbc" in src) and len(src) > 30:
                if src.startswith("//"):
                    src = "https:" + src
                urls.append(src)
    except Exception as e:
        print(f"  KB error: {e}")
    return urls


async def crawl_autobell(page, query: str) -> list[str]:
    """오토벨에서 이미지"""
    urls = []
    try:
        search_url = f"https://www.autobell.co.kr/search?q={query}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(3000)

        images = await page.query_selector_all("img[src*='http']")
        for img in images[:20]:
            src = await img.get_attribute("src") or ""
            if src and "autobell" in src and len(src) > 30:
                urls.append(src)
    except Exception as e:
        print(f"  Autobell error: {e}")
    return urls


async def main():
    print("=== 최종 차량 이미지 크롤러 ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        for car in CARS:
            filepath = SAVE_DIR / car["filename"]

            # 이미 좋은 이미지가 있으면 스킵
            if filepath.exists():
                from PIL import Image
                try:
                    img = Image.open(filepath)
                    if img.size[1] >= car["min_h"] and filepath.stat().st_size > 20000:
                        print(f"[{car['id']:2d}] {car['query']} → OK ({img.size[0]}x{img.size[1]}, {filepath.stat().st_size // 1024}KB)")
                        continue
                except:
                    pass

            print(f"[{car['id']:2d}] {car['query']} 크롤링...")

            all_urls = []

            # 1. 엔카
            encar_urls = await crawl_encar_listing(page, car["query"])
            all_urls.extend(encar_urls)
            print(f"  Encar: {len(encar_urls)} URLs")

            # 2. KB차차차
            kb_urls = await crawl_kbchacha(page, car["query"])
            all_urls.extend(kb_urls)
            print(f"  KB: {len(kb_urls)} URLs")

            # 다운로드 + 검증
            downloaded = False
            for url in all_urls:
                if await download_and_verify(url, filepath, car["min_h"]):
                    from PIL import Image
                    img = Image.open(filepath)
                    print(f"  ✓ {car['filename']} ({img.size[0]}x{img.size[1]}, {filepath.stat().st_size // 1024}KB)")
                    downloaded = True
                    break

            if not downloaded:
                print(f"  ✗ 적합한 이미지를 찾지 못함")

            await page.wait_for_timeout(1500)

        await browser.close()

    # 최종 결과
    print(f"\n=== 최종 결과 ===")
    from PIL import Image
    for car in CARS:
        filepath = SAVE_DIR / car["filename"]
        if filepath.exists():
            try:
                img = Image.open(filepath)
                status = "OK" if img.size[1] >= 200 else "LQ"
                print(f"  [{status}] {car['filename']:20s} {img.size[0]:4d}x{img.size[1]:<4d} {filepath.stat().st_size // 1024:>4d}KB")
            except:
                print(f"  [??] {car['filename']}")
        else:
            print(f"  [--] {car['filename']:20s} 없음")


if __name__ == "__main__":
    asyncio.run(main())
