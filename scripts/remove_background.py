#!/usr/bin/env python3
"""
배경 제거 스크립트 — rembg를 사용하여 RGBA PNG 생성
GS alpha_mask 지원과 호환: RGBA 이미지를 원래 파일명(.jpg)으로 저장
PIL은 파일 헤더로 포맷을 감지하므로 확장자와 무관하게 RGBA로 로드됨
"""

import argparse
import os
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def remove_background_single(
    input_path: str,
    output_path: str,
    session,
    alpha_matting: bool = True,
):
    """단일 이미지의 배경을 제거하고 RGBA PNG로 저장한다."""
    from rembg import remove

    img = Image.open(input_path).convert("RGB")

    result = remove(
        img,
        session=session,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10,
    )

    # RGBA로 변환 (이미 RGBA일 수 있지만 확실히)
    result = result.convert("RGBA")
    r, g, b, a = result.split()

    # 배경(alpha=0) 영역의 RGB를 검정(0)으로 강제
    r_arr = np.array(r)
    g_arr = np.array(g)
    b_arr = np.array(b)
    a_arr = np.array(a)

    mask = a_arr == 0
    r_arr[mask] = 0
    g_arr[mask] = 0
    b_arr[mask] = 0

    final = Image.merge("RGBA", [
        Image.fromarray(r_arr),
        Image.fromarray(g_arr),
        Image.fromarray(b_arr),
        Image.fromarray(a_arr),
    ])

    # PNG로 저장 (파일명은 .jpg 유지 — PIL은 헤더로 포맷 감지)
    final.save(output_path, format="PNG")
    return os.path.basename(output_path)


def main():
    parser = argparse.ArgumentParser(description="rembg를 사용한 배경 제거 (RGBA PNG 출력)")
    parser.add_argument("--input_dir", required=True, help="입력 이미지 폴더")
    parser.add_argument("--output_dir", required=True, help="출력 이미지 폴더")
    parser.add_argument(
        "--model",
        default="u2net",
        choices=["u2net", "u2netp", "u2net_human_seg", "isnet-general-use"],
        help="rembg 모델 (기본값: u2net)",
    )
    parser.add_argument("--no_alpha_matting", action="store_true", help="alpha matting 비활성화")
    parser.add_argument("--workers", type=int, default=1, help="병렬 워커 수 (GPU 모델이므로 1 권장)")
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir)

    if not os.path.isdir(input_dir):
        logger.error(f"입력 폴더가 존재하지 않습니다: {input_dir}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # 이미지 파일 목록
    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
    image_files = sorted([
        f for f in os.listdir(input_dir)
        if os.path.splitext(f)[1].lower() in extensions
    ])

    if not image_files:
        logger.error(f"입력 폴더에 이미지가 없습니다: {input_dir}")
        sys.exit(1)

    logger.info(f"배경 제거 시작: {len(image_files)}개 이미지")
    logger.info(f"  입력: {input_dir}")
    logger.info(f"  출력: {output_dir}")
    logger.info(f"  모델: {args.model}")
    logger.info(f"  alpha matting: {not args.no_alpha_matting}")

    # rembg 세션 한 번만 로드
    from rembg import new_session
    session = new_session(args.model)

    # 이미 처리된 파일 건너뛰기
    todo_files = []
    skipped = 0
    for fname in image_files:
        out = os.path.join(output_dir, fname)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            skipped += 1
        else:
            todo_files.append(fname)

    if skipped > 0:
        logger.info(f"  이미 처리된 파일 {skipped}개 건너뜀, 남은 {len(todo_files)}개 처리")

    start = time.time()
    completed = 0

    for fname in todo_files:
        input_path = os.path.join(input_dir, fname)
        output_path = os.path.join(output_dir, fname)

        try:
            remove_background_single(
                input_path, output_path, session,
                alpha_matting=not args.no_alpha_matting,
            )
            completed += 1
            elapsed = time.time() - start
            avg = elapsed / completed
            remaining = avg * (len(todo_files) - completed)
            total_done = skipped + completed
            logger.info(
                f"  [{total_done}/{len(image_files)}] {fname} "
                f"(경과: {elapsed:.0f}s, 남은: {remaining:.0f}s)"
            )
        except Exception as e:
            logger.error(f"  [실패] {fname}: {e}")

    elapsed = time.time() - start
    total_done = skipped + completed
    logger.info(f"배경 제거 완료: {total_done}/{len(image_files)}개 ({elapsed:.1f}초, 신규 {completed}개)")


if __name__ == "__main__":
    main()
