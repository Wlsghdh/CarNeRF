#!/usr/bin/env python3
"""
학습된 Gaussian Splatting 모델을 웹 뷰어용으로 변환/export
- .ply 파일을 경량화된 .ply 또는 .splat 형식으로 변환
- 가우시안 개수가 100만 개 이상이면 opacity 기준 pruning
"""

import argparse
import os
import sys
import logging

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def read_ply(ply_path: str) -> dict:
    """PLY 파일을 읽어서 가우시안 데이터를 반환한다."""
    try:
        from plyfile import PlyData
    except ImportError:
        logger.error("plyfile 패키지가 필요합니다: pip install plyfile")
        sys.exit(1)

    logger.info(f"PLY 파일 읽는 중: {ply_path}")
    plydata = PlyData.read(ply_path)
    vertex = plydata["vertex"]

    logger.info(f"가우시안 개수: {len(vertex.data):,}개")
    logger.info(f"속성: {[p.name for p in vertex.properties]}")

    return plydata


def sigmoid(x):
    """시그모이드 함수"""
    return 1.0 / (1.0 + np.exp(-x))


def prune_by_opacity(plydata, max_gaussians: int = 1_000_000, min_opacity: float = 0.005):
    """
    Opacity가 낮은 가우시안을 제거한다.
    Gaussian Splatting에서 opacity는 sigmoid(opacity_raw) 형태로 저장됨.
    """
    vertex = plydata["vertex"]
    num_gaussians = len(vertex.data)

    if num_gaussians <= max_gaussians:
        logger.info(f"가우시안 수({num_gaussians:,})가 {max_gaussians:,} 이하이므로 pruning 불필요")
        return plydata

    logger.info(f"가우시안 수({num_gaussians:,})가 {max_gaussians:,}을 초과하여 pruning 시작...")

    # opacity 값 추출 (속성 이름은 'opacity')
    property_names = [p.name for p in vertex.properties]

    if "opacity" in property_names:
        opacity_raw = vertex["opacity"]
        opacity = sigmoid(opacity_raw)
    else:
        logger.warning("opacity 속성을 찾을 수 없습니다. pruning을 건너뜁니다.")
        return plydata

    # 1차: 최소 opacity로 필터링
    mask = opacity >= min_opacity
    remaining = np.sum(mask)
    logger.info(f"  opacity >= {min_opacity} 필터링: {num_gaussians:,} → {remaining:,}")

    # 2차: 여전히 너무 많으면 opacity 높은 순으로 상위 max_gaussians개 선택
    if remaining > max_gaussians:
        indices = np.where(mask)[0]
        opacity_filtered = opacity[indices]
        top_indices = np.argsort(opacity_filtered)[-max_gaussians:]
        final_indices = indices[top_indices]
        mask = np.zeros(num_gaussians, dtype=bool)
        mask[final_indices] = True
        logger.info(f"  상위 opacity 선택: {remaining:,} → {max_gaussians:,}")

    # 필터링 적용
    from plyfile import PlyData, PlyElement
    filtered_data = vertex.data[mask]
    new_vertex = PlyElement.describe(filtered_data, "vertex")
    new_plydata = PlyData([new_vertex])

    logger.info(f"pruning 완료: {num_gaussians:,} → {len(filtered_data):,}")
    return new_plydata


def prune_by_volume(plydata, max_scale_factor: float = 10.0, max_aspect_ratio: float = 50.0):
    """
    볼륨 기반 pruning: 극단적 스케일/종횡비의 가우시안 제거.
    - max_scale_factor: 스케일 중간값 대비 이 배수 이상인 가우시안 제거
    - max_aspect_ratio: 가장 큰 축 / 가장 작은 축 비율 제한
    """
    vertex = plydata["vertex"]
    num_gaussians = len(vertex.data)
    property_names = [p.name for p in vertex.properties]

    if "scale_0" not in property_names:
        logger.info("scale 속성이 없어 볼륨 pruning을 건너뜁니다.")
        return plydata

    # 스케일 추출 (log space → exp)
    sx = np.exp(vertex["scale_0"].astype(np.float32))
    sy = np.exp(vertex["scale_1"].astype(np.float32))
    if "scale_2" in property_names:
        sz = np.exp(vertex["scale_2"].astype(np.float32))
        scales = np.stack([sx, sy, sz], axis=1)
    else:
        # 2DGS: only 2 scales
        scales = np.stack([sx, sy], axis=1)
    max_scale = scales.max(axis=1)
    min_scale = scales.min(axis=1)

    # 중간값 기준 극단적 크기 제거
    median_max_scale = np.median(max_scale)
    scale_mask = max_scale <= median_max_scale * max_scale_factor

    # 종횡비 제한
    aspect_ratio = max_scale / np.maximum(min_scale, 1e-10)
    aspect_mask = aspect_ratio <= max_aspect_ratio

    mask = scale_mask & aspect_mask
    removed_scale = num_gaussians - np.sum(scale_mask)
    removed_aspect = num_gaussians - np.sum(aspect_mask)
    remaining = np.sum(mask)

    logger.info(f"볼륨 pruning: {num_gaussians:,} → {remaining:,}")
    logger.info(f"  큰 스케일 제거: {removed_scale:,} (>{max_scale_factor}x median)")
    logger.info(f"  높은 종횡비 제거: {removed_aspect:,} (>{max_aspect_ratio}:1)")

    if remaining == num_gaussians:
        return plydata

    from plyfile import PlyData, PlyElement
    filtered_data = vertex.data[mask]
    new_vertex = PlyElement.describe(filtered_data, "vertex")
    return PlyData([new_vertex])


def prune_by_spatial_outliers(plydata, iqr_factor: float = 4.0):
    """
    IQR 기반 공간적 outlier 제거.
    각 축별로 Q1 - factor*IQR ~ Q3 + factor*IQR 범위 밖의 Gaussian 제거.
    차에서 멀리 떨어진 부유/가시 아티팩트 제거에 효과적.
    """
    vertex = plydata["vertex"]
    num_gaussians = len(vertex.data)

    x = vertex["x"].astype(np.float32)
    y = vertex["y"].astype(np.float32)
    z = vertex["z"].astype(np.float32)

    mask = np.ones(num_gaussians, dtype=bool)

    for axis_name, coords in [("x", x), ("y", y), ("z", z)]:
        q1, q3 = np.percentile(coords, [25, 75])
        iqr = q3 - q1
        lo = q1 - iqr_factor * iqr
        hi = q3 + iqr_factor * iqr
        axis_mask = (coords >= lo) & (coords <= hi)
        removed = int(np.sum(~axis_mask))
        if removed > 0:
            logger.info(f"  {axis_name}축 공간 outlier 제거: {removed:,}개 (유효 범위: {lo:.3f}~{hi:.3f})")
        mask &= axis_mask

    remaining = int(np.sum(mask))
    logger.info(f"공간 outlier pruning: {num_gaussians:,} → {remaining:,}")

    if remaining == num_gaussians:
        return plydata

    from plyfile import PlyData, PlyElement
    filtered_data = vertex.data[mask]
    new_vertex = PlyElement.describe(filtered_data, "vertex")
    return PlyData([new_vertex])


def export_ply(plydata, output_path: str):
    """경량화된 PLY 파일로 저장한다."""
    logger.info(f"PLY 저장 중: {output_path}")
    plydata.write(output_path)
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    logger.info(f"저장 완료: {file_size_mb:.1f} MB")


def export_splat(plydata, output_path: str):
    """
    .splat 형식으로 변환하여 저장한다.
    .splat 형식: 각 가우시안당 32바이트
    - position (3 x float32 = 12 bytes) -> x, y, z
    - scale (3 x float32 → log scale → 정규화) -> 3 bytes
    - color (3 x uint8) -> r, g, b -> 3 bytes (SH의 DC 성분)
    - opacity (1 x uint8) -> 1 byte
    - rotation (4 x uint8) -> quaternion 정규화 -> 4 bytes (나머지 padding)

    참고: antimatter15/splat 포맷 호환
    """
    vertex = plydata["vertex"]
    num = len(vertex.data)
    property_names = [p.name for p in vertex.properties]

    logger.info(f".splat 형식으로 변환 중 (가우시안 {num:,}개)...")

    # Position
    x = vertex["x"].astype(np.float32)
    y = vertex["y"].astype(np.float32)
    z = vertex["z"].astype(np.float32)

    # Scale (log space)
    if "scale_0" in property_names:
        sx = vertex["scale_0"].astype(np.float32)
        sy = vertex["scale_1"].astype(np.float32)
        if "scale_2" in property_names:
            sz = vertex["scale_2"].astype(np.float32)
        else:
            # 2DGS (surfel): only 2 scales, third dimension is near-zero thickness
            logger.info("2DGS 감지: scale_2 없음 → 얇은 디스크로 설정 (log_scale=-7)")
            sz = np.full(num, -7.0, dtype=np.float32)
    else:
        logger.warning("scale 속성이 없습니다. 기본값 사용")
        sx = sy = sz = np.zeros(num, dtype=np.float32)

    # Rotation (quaternion)
    if "rot_0" in property_names:
        rw = vertex["rot_0"].astype(np.float32)
        rx = vertex["rot_1"].astype(np.float32)
        ry = vertex["rot_2"].astype(np.float32)
        rz = vertex["rot_3"].astype(np.float32)
    else:
        logger.warning("rotation 속성이 없습니다. 기본값 사용")
        rw = np.ones(num, dtype=np.float32)
        rx = ry = rz = np.zeros(num, dtype=np.float32)

    # Normalize quaternion
    norm = np.sqrt(rw**2 + rx**2 + ry**2 + rz**2)
    norm = np.maximum(norm, 1e-10)
    rw /= norm
    rx /= norm
    ry /= norm
    rz /= norm

    # Color (SH DC 성분에서 추출)
    SH_C0 = 0.28209479177387814
    if "f_dc_0" in property_names:
        r = (0.5 + SH_C0 * vertex["f_dc_0"]).clip(0, 1)
        g = (0.5 + SH_C0 * vertex["f_dc_1"]).clip(0, 1)
        b = (0.5 + SH_C0 * vertex["f_dc_2"]).clip(0, 1)
    else:
        # fallback: red, green, blue 속성
        r = (vertex.get("red", np.ones(num) * 128) / 255.0).clip(0, 1)
        g = (vertex.get("green", np.ones(num) * 128) / 255.0).clip(0, 1)
        b = (vertex.get("blue", np.ones(num) * 128) / 255.0).clip(0, 1)

    # Opacity
    if "opacity" in property_names:
        opacity = sigmoid(vertex["opacity"]).clip(0, 1)
    else:
        opacity = np.ones(num, dtype=np.float32)

    # .splat 파일 쓰기 (antimatter15 포맷: 각 가우시안 32바이트) — 벡터화
    # structured array로 한번에 구성 후 tofile()로 저장
    splat_dtype = np.dtype([
        ("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
        ("sx", "<f4"), ("sy", "<f4"), ("sz", "<f4"),
        ("r", "u1"), ("g", "u1"), ("b", "u1"), ("a", "u1"),
        ("rw", "u1"), ("rx", "u1"), ("ry", "u1"), ("rz", "u1"),
    ])
    splat_data = np.empty(num, dtype=splat_dtype)
    splat_data["x"] = x
    splat_data["y"] = y
    splat_data["z"] = z
    splat_data["sx"] = np.exp(sx)
    splat_data["sy"] = np.exp(sy)
    splat_data["sz"] = np.exp(sz)
    splat_data["r"] = (r * 255).clip(0, 255).astype(np.uint8)
    splat_data["g"] = (g * 255).clip(0, 255).astype(np.uint8)
    splat_data["b"] = (b * 255).clip(0, 255).astype(np.uint8)
    splat_data["a"] = (opacity * 255).clip(0, 255).astype(np.uint8)
    splat_data["rw"] = ((rw * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    splat_data["rx"] = ((rx * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    splat_data["ry"] = ((ry * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    splat_data["rz"] = ((rz * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)

    splat_data.tofile(output_path)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    logger.info(f".splat 저장 완료: {output_path} ({file_size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Gaussian Splatting 모델을 웹 뷰어용으로 변환")
    parser.add_argument("--input", required=True, help="학습된 point_cloud.ply 경로")
    parser.add_argument("--output", required=True, help="변환 결과 저장 경로 (파일 또는 디렉토리)")
    parser.add_argument("--format", choices=["ply", "splat", "both"], default="both", help="출력 형식 (기본값: both)")
    parser.add_argument("--max_gaussians", type=int, default=1_000_000, help="최대 가우시안 수 (기본값: 1,000,000)")
    parser.add_argument("--max_scale_factor", type=float, default=0, help="볼륨 pruning: 스케일 중간값 대비 최대 배수 (0=비활성)")
    parser.add_argument("--max_aspect_ratio", type=float, default=0, help="볼륨 pruning: 최대 종횡비 (0=비활성)")
    parser.add_argument("--spatial_iqr", type=float, default=0, help="공간 outlier 제거: IQR 배수 (0=비활성, 권장 3.0~5.0)")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)

    if not os.path.exists(input_path):
        logger.error(f"입력 파일이 존재하지 않습니다: {input_path}")
        sys.exit(1)

    # 출력 경로 처리
    if os.path.isdir(output_path) or not os.path.splitext(output_path)[1]:
        os.makedirs(output_path, exist_ok=True)
        output_dir = output_path
    else:
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

    # PLY 읽기
    plydata = read_ply(input_path)

    # 1. 공간 outlier 제거 (IQR 기반 — 차에서 먼 부유/가시 아티팩트)
    if args.spatial_iqr > 0:
        plydata = prune_by_spatial_outliers(plydata, iqr_factor=args.spatial_iqr)

    # 2. Volume-based pruning (극단적 종횡비/스케일 가우시안 제거)
    if args.max_scale_factor > 0 or args.max_aspect_ratio > 0:
        plydata = prune_by_volume(
            plydata,
            max_scale_factor=args.max_scale_factor if args.max_scale_factor > 0 else 10.0,
            max_aspect_ratio=args.max_aspect_ratio if args.max_aspect_ratio > 0 else 50.0,
        )

    # 3. Opacity-based pruning (투명한 배경 가우시안 제거 + 수량 제한)
    plydata = prune_by_opacity(plydata, max_gaussians=args.max_gaussians)

    # Export
    if args.format in ("ply", "both"):
        ply_output = os.path.join(output_dir, "model.ply") if os.path.isdir(output_path) else output_path
        export_ply(plydata, ply_output)

    if args.format in ("splat", "both"):
        splat_output = os.path.join(output_dir, "model.splat") if os.path.isdir(output_path) else output_path.replace(".ply", ".splat")
        export_splat(plydata, splat_output)

    logger.info("모델 변환 완료!")


if __name__ == "__main__":
    main()
