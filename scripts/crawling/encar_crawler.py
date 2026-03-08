"""
엔카(Encar.com) 중고차 데이터 크롤러
- api.encar.com JSON API 사용 (인증 불필요)
- 국산차 + 수입차 전체 수집
- CSV 저장 (data/car_prices.csv)
- Ctrl+C로 중단해도 그때까지 수집된 데이터 저장
"""

import requests
import csv
import time
import random
import os
import signal
import sys
from datetime import datetime

# === 설정 ===
BASE_URL = "http://api.encar.com/search/car/list/general"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "car_prices.csv")
PAGE_SIZE = 50
MIN_DELAY = 1.0
MAX_DELAY = 2.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "http://www.encar.com/",
}

# 수집할 제조사 목록 (국산 + 수입)
MANUFACTURERS = [
    # 국산
    "현대", "기아", "제네시스", "쉐보레(GM대우)", "르노코리아(삼성)", "쌍용", "KG모빌리티",
    # 수입
    "BMW", "벤츠", "아우디", "폭스바겐", "볼보", "토요타", "렉서스", "혼다",
    "포르쉐", "랜드로버", "미니", "지프", "푸조", "테슬라", "폴스타",
]

CSV_FIELDS = [
    "id", "brand", "model", "badge", "badge_detail",
    "year", "form_year", "mileage", "price",
    "fuel_type", "transmission", "color",
    "region", "sell_type",
    "green_type", "ev_type",
    "photo_url", "encar_url",
    "crawled_at",
]

# 글로벌 상태
total_collected = 0
writer = None
csv_file = None
stop_flag = False


def signal_handler(sig, frame):
    global stop_flag
    print(f"\n\n[중단] 시그널 수신. 지금까지 {total_collected}건 수집 완료. 저장 중...")
    stop_flag = True


def fetch_listings(manufacturer, offset=0, page_size=PAGE_SIZE):
    """엔카 API에서 매물 목록 조회"""
    q = f"(And.Hidden.N._.CarType.Y._.Manufacturer.{manufacturer}.)"
    params = {
        "count": "true",
        "q": q,
        "sr": f"|ModifiedDate|{offset}|{page_size}",
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [에러] {manufacturer} offset={offset}: {e}")
        return None


def fetch_car_detail(car_id):
    """개별 차량 상세 정보 조회 (옵션, 사고이력 등)"""
    url = f"http://api.encar.com/search/car/list/premium?count=false&q=(And.Hidden.N._.Id.{car_id}.)"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("SearchResults"):
            return data["SearchResults"][0]
    except Exception:
        pass
    return None


def parse_year(year_val):
    """202311.0 -> 2023"""
    if year_val is None:
        return ""
    try:
        return str(int(float(year_val) // 100))
    except (ValueError, TypeError):
        return str(year_val)


def parse_listing(item, manufacturer):
    """API 응답 항목을 CSV row로 변환"""
    car_id = item.get("Id", "")
    photo = item.get("Photo", "")
    photo_url = f"https://ci.encar.com{photo}001.jpg" if photo else ""

    return {
        "id": car_id,
        "brand": manufacturer,
        "model": item.get("Model", ""),
        "badge": item.get("Badge", ""),
        "badge_detail": item.get("BadgeDetail", ""),
        "year": parse_year(item.get("Year")),
        "form_year": item.get("FormYear", ""),
        "mileage": int(item.get("Mileage", 0) or 0),
        "price": int(item.get("Price", 0) or 0),
        "fuel_type": item.get("FuelType", ""),
        "transmission": item.get("Transmission", ""),
        "color": item.get("Color", ""),
        "region": item.get("OfficeCityState", ""),
        "sell_type": item.get("SellType", ""),
        "green_type": item.get("GreenType", ""),
        "ev_type": item.get("EvType", ""),
        "photo_url": photo_url,
        "encar_url": f"http://www.encar.com/dc/dc_cardetailview.do?carid={car_id}",
        "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def crawl_manufacturer(manufacturer):
    """한 제조사의 전체 매물 수집"""
    global total_collected, stop_flag

    # 첫 요청으로 총 건수 확인
    data = fetch_listings(manufacturer, offset=0, page_size=1)
    if not data:
        print(f"  [스킵] {manufacturer}: API 응답 없음")
        return

    total_count = data.get("Count", 0)
    print(f"  {manufacturer}: 총 {total_count:,}건 발견")

    if total_count == 0:
        return

    offset = 0
    collected_for_brand = 0

    while offset < total_count and not stop_flag:
        data = fetch_listings(manufacturer, offset=offset, page_size=PAGE_SIZE)
        if not data or "SearchResults" not in data:
            print(f"  [에러] {manufacturer} offset={offset}: 결과 없음, 다음 제조사로")
            break

        results = data["SearchResults"]
        if not results:
            break

        for item in results:
            if stop_flag:
                break
            row = parse_listing(item, manufacturer)
            if row["price"] > 0:  # 가격 없는 매물 제외
                writer.writerow(row)
                total_collected += 1
                collected_for_brand += 1

        offset += PAGE_SIZE

        # 진행 상황 출력 (500건마다)
        if collected_for_brand % 500 < PAGE_SIZE:
            print(f"    {manufacturer}: {collected_for_brand:,}/{total_count:,}건 수집 (전체: {total_collected:,}건)")
            csv_file.flush()

        # rate limiting
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    print(f"  [완료] {manufacturer}: {collected_for_brand:,}건 수집")


def crawl_import_cars():
    """수입차는 CarType.N으로 별도 조회"""
    global total_collected, stop_flag

    import_brands = ["BMW", "벤츠", "아우디", "폭스바겐", "볼보", "토요타",
                     "렉서스", "혼다", "포르쉐", "랜드로버", "미니", "지프",
                     "푸조", "테슬라", "폴스타"]

    for brand in import_brands:
        if stop_flag:
            break
        print(f"\n[수입차] {brand} 수집 시작...")

        q = f"(And.Hidden.N._.CarType.N._.Manufacturer.{brand}.)"
        params = {
            "count": "true",
            "q": q,
            "sr": "|ModifiedDate|0|1",
        }
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
            data = resp.json()
            total_count = data.get("Count", 0)
            print(f"  {brand}: 총 {total_count:,}건 발견")
        except Exception as e:
            print(f"  [에러] {brand}: {e}")
            continue

        if total_count == 0:
            continue

        offset = 0
        collected = 0

        while offset < total_count and not stop_flag:
            params["sr"] = f"|ModifiedDate|{offset}|{PAGE_SIZE}"
            try:
                resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
                data = resp.json()
                results = data.get("SearchResults", [])
            except Exception:
                break

            if not results:
                break

            for item in results:
                if stop_flag:
                    break
                row = parse_listing(item, brand)
                if row["price"] > 0:
                    writer.writerow(row)
                    total_collected += 1
                    collected += 1

            offset += PAGE_SIZE

            if collected % 500 < PAGE_SIZE:
                print(f"    {brand}: {collected:,}/{total_count:,}건 (전체: {total_collected:,}건)")
                csv_file.flush()

            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        print(f"  [완료] {brand}: {collected:,}건 수집")


def main():
    global writer, csv_file, total_collected

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 이어쓰기 지원: 기존 파일 있으면 append
    file_exists = os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0

    if file_exists:
        # 기존 데이터 건수 세기
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = sum(1 for _ in f) - 1  # 헤더 제외
        total_collected = existing
        print(f"[이어쓰기] 기존 {existing:,}건 존재. 이어서 수집합니다.\n")
        csv_file = open(OUTPUT_FILE, "a", newline="", encoding="utf-8")
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
    else:
        csv_file = open(OUTPUT_FILE, "w", newline="", encoding="utf-8")
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        print("[새로 시작] car_prices.csv 생성\n")

    start_time = datetime.now()
    print(f"=== 엔카 중고차 크롤링 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"저장 경로: {OUTPUT_FILE}")
    print(f"Ctrl+C로 중단하면 그때까지 수집된 데이터가 저장됩니다.\n")

    # 국산차 수집
    domestic_brands = ["현대", "기아", "제네시스", "쉐보레(GM대우)", "르노코리아(삼성)", "쌍용", "KG모빌리티"]

    for brand in domestic_brands:
        if stop_flag:
            break
        print(f"\n[국산차] {brand} 수집 시작...")

        q = f"(And.Hidden.N._.CarType.Y._.Manufacturer.{brand}.)"
        params = {
            "count": "true",
            "q": q,
            "sr": "|ModifiedDate|0|1",
        }
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
            data = resp.json()
            total_count = data.get("Count", 0)
            print(f"  {brand}: 총 {total_count:,}건 발견")
        except Exception as e:
            print(f"  [에러] {brand}: {e}")
            continue

        if total_count == 0:
            continue

        offset = 0
        collected = 0

        while offset < total_count and not stop_flag:
            params["sr"] = f"|ModifiedDate|{offset}|{PAGE_SIZE}"
            try:
                resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
                data = resp.json()
                results = data.get("SearchResults", [])
            except Exception:
                break

            if not results:
                break

            for item in results:
                if stop_flag:
                    break
                row = parse_listing(item, brand)
                if row["price"] > 0:
                    writer.writerow(row)
                    total_collected += 1
                    collected += 1

            offset += PAGE_SIZE

            if collected % 500 < PAGE_SIZE:
                print(f"    {brand}: {collected:,}/{total_count:,}건 (전체: {total_collected:,}건)")
                csv_file.flush()

            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        print(f"  [완료] {brand}: {collected:,}건 수집")

    # 수입차 수집
    if not stop_flag:
        crawl_import_cars()

    # 모든 제조사 완료 후, 다시 처음부터 반복 (kill 전까지)
    round_num = 2
    while not stop_flag:
        print(f"\n\n=== 라운드 {round_num} 시작 (전체: {total_collected:,}건) ===\n")

        all_brands_domestic = [
            ("Y", b) for b in domestic_brands
        ]
        all_brands_import = [
            ("N", b) for b in ["BMW", "벤츠", "아우디", "폭스바겐", "볼보", "토요타",
                               "렉서스", "혼다", "포르쉐", "랜드로버", "미니", "지프",
                               "푸조", "테슬라", "폴스타"]
        ]

        for car_type, brand in all_brands_domestic + all_brands_import:
            if stop_flag:
                break

            q = f"(And.Hidden.N._.CarType.{car_type}._.Manufacturer.{brand}.)"
            params = {
                "count": "true",
                "q": q,
                "sr": "|ModifiedDate|0|1",
            }
            try:
                resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
                data = resp.json()
                total_count = data.get("Count", 0)
            except Exception:
                continue

            if total_count == 0:
                continue

            print(f"  [{brand}] {total_count:,}건 재수집 중...")
            offset = 0
            collected = 0

            while offset < total_count and not stop_flag:
                params["sr"] = f"|ModifiedDate|{offset}|{PAGE_SIZE}"
                try:
                    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
                    data = resp.json()
                    results = data.get("SearchResults", [])
                except Exception:
                    break

                if not results:
                    break

                for item in results:
                    if stop_flag:
                        break
                    row = parse_listing(item, brand)
                    if row["price"] > 0:
                        writer.writerow(row)
                        total_collected += 1
                        collected += 1

                offset += PAGE_SIZE

                if collected % 1000 < PAGE_SIZE:
                    print(f"    {brand}: {collected:,}건 (전체: {total_collected:,}건)")
                    csv_file.flush()

                time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        round_num += 1

    # 종료
    csv_file.flush()
    csv_file.close()
    elapsed = datetime.now() - start_time
    print(f"\n=== 크롤링 종료 ===")
    print(f"총 수집: {total_collected:,}건")
    print(f"소요 시간: {elapsed}")
    print(f"저장 파일: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
