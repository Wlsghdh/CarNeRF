"""
홈페이지 히어로 섹션용 프리미엄 이미지 크롤링
- Unsplash에서 고품질 무료 자동차/기술 이미지
"""
import asyncio
import httpx
from pathlib import Path
from playwright.async_api import async_playwright

SAVE_DIR = Path("/home/jjh0709/Project_2026_1/backend/app/static/images/hero")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# 각 슬라이드별 검색어와 파일명
HERO_IMAGES = [
    {"query": "car technology scan futuristic dark", "filename": "hero_neural.jpg"},
    {"query": "car price graph analytics dashboard dark", "filename": "hero_estimation.jpg"},
    {"query": "luxury car showroom dark premium", "filename": "hero_reliable.jpg"},
    {"query": "car deal handshake trust dark", "filename": "hero_fair.jpg"},
]


async def download_image(url: str, filepath: Path, min_size: int = 30000) -> bool:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            })
            if resp.status_code == 200 and len(resp.content) > min_size:
                # Resize to reasonable web size
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(resp.content))
                w, h = img.size
                if w > 1920:
                    ratio = 1920 / w
                    img = img.resize((1920, int(h * ratio)), Image.LANCZOS)
                img.save(filepath, "JPEG", quality=85, optimize=True)
                return True
    except Exception as e:
        print(f"    Download error: {e}")
    return False


async def search_unsplash(page, query: str) -> list[str]:
    """Unsplash에서 고품질 무료 이미지 URL 수집"""
    urls = []
    try:
        search_url = f"https://unsplash.com/s/photos/{query.replace(' ', '-')}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)

        # Unsplash 이미지 태그
        images = await page.query_selector_all("img[srcset], img[src*='images.unsplash']")
        for img in images[:15]:
            srcset = await img.get_attribute("srcset") or ""
            src = await img.get_attribute("src") or ""

            # srcset에서 가장 큰 이미지 추출
            if srcset:
                parts = srcset.split(",")
                for part in reversed(parts):
                    url = part.strip().split(" ")[0]
                    if "images.unsplash.com" in url and url not in urls:
                        urls.append(url)
                        break
            elif "images.unsplash.com" in src and src not in urls:
                urls.append(src)
    except Exception as e:
        print(f"    Unsplash error: {e}")
    return urls


async def search_pexels(page, query: str) -> list[str]:
    """Pexels에서 무료 이미지"""
    urls = []
    try:
        search_url = f"https://www.pexels.com/search/{query.replace(' ', '%20')}/"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(3000)

        images = await page.query_selector_all("img[src*='pexels'], img[srcset*='pexels']")
        for img in images[:10]:
            src = await img.get_attribute("src") or ""
            if "images.pexels.com" in src and "photo" in src:
                # 큰 사이즈로 변환
                if "?auto=" in src:
                    src = src.split("?")[0] + "?auto=compress&cs=tinysrgb&w=1920"
                urls.append(src)
    except Exception as e:
        print(f"    Pexels error: {e}")
    return urls


async def main():
    print("=== 히어로 이미지 크롤러 ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        for item in HERO_IMAGES:
            filepath = SAVE_DIR / item["filename"]
            if filepath.exists() and filepath.stat().st_size > 30000:
                print(f"  ✓ {item['filename']} 이미 존재")
                continue

            print(f"  {item['filename']} ({item['query']})...")

            all_urls = []

            # Unsplash
            urls = await search_unsplash(page, item["query"])
            all_urls.extend(urls)
            print(f"    Unsplash: {len(urls)} URLs")

            # Pexels
            if len(all_urls) < 3:
                urls = await search_pexels(page, item["query"])
                all_urls.extend(urls)
                print(f"    Pexels: {len(urls)} URLs")

            downloaded = False
            for url in all_urls:
                if await download_image(url, filepath):
                    from PIL import Image
                    img = Image.open(filepath)
                    print(f"    ✓ {img.size[0]}x{img.size[1]} ({filepath.stat().st_size // 1024}KB)")
                    downloaded = True
                    break

            if not downloaded:
                print(f"    ✗ 이미지 못 찾음")

            await page.wait_for_timeout(2000)

        await browser.close()

    print(f"\n=== 결과 ===")
    for item in HERO_IMAGES:
        filepath = SAVE_DIR / item["filename"]
        if filepath.exists():
            from PIL import Image
            img = Image.open(filepath)
            print(f"  ✓ {item['filename']:25s} {img.size[0]}x{img.size[1]} {filepath.stat().st_size // 1024}KB")
        else:
            print(f"  ✗ {item['filename']}")


if __name__ == "__main__":
    asyncio.run(main())
