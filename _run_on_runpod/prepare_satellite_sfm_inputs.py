#!/usr/bin/env python3
"""
カスタム衛星画像データを satellite_sfm.py の入力形式に整えるスクリプト。

以下の処理を行う:
  1. output_dir/images/ を作成し、tif_dir から TIF ファイルをスケーリング変換してコピー
     - uint16 画像を uint8 にスケーリング（RPC メタデータは保持）
     - スケーリング方式: linear（デフォルト）, bitshift, percentile
     - BlackSky等のメタデータJSONから撮影日時を読み込み NITF_IDATIM として埋め込み
  2. TIF の RPC メタデータから latlonalt_bbx.json を生成して output_dir/ に配置

=== 生成されるディレクトリ構造 ===

  <output_dir>/
  ├── images/
  │   ├── image_001.tif
  │   ├── image_002.tif
  │   └── ...
  └── latlonalt_bbx.json

=== 使い方 ===

1. conda環境をアクティベート:
   $ conda activate SatelliteSfM

2. 基本的な使い方:
   $ python _run_on_runpod/prepare_satellite_sfm_inputs.py \
       --tif_dir data/BSG-STEREO-MF-117-20260114-023900-417077014/BSG-STEREO-MF-117-20260114-023900-417077014 \
       --output_dir data/BSG-STEREO-MF-117-20260114-023900-417077014/inputs

3. TIFファイル名のパターンを指定（デフォルト: *.tif）:
   $ python _run_on_runpod/prepare_satellite_sfm_inputs.py \
       --tif_dir /path/to/tifs \
       --output_dir /path/to/inputs \
       --pattern "*_georeferenced.tif"

4. 高度範囲を手動指定:
   $ python _run_on_runpod/prepare_satellite_sfm_inputs.py \
       --tif_dir /path/to/tifs \
       --output_dir /path/to/inputs \
       --alt_min -30 --alt_max 300

5. スケーリング方式を指定（デフォルト: linear）:
   $ python _run_on_runpod/prepare_satellite_sfm_inputs.py \
       --tif_dir /path/to/tifs \
       --output_dir /path/to/inputs \
       --scale_method percentile

   スケーリング方式:
     linear     : 線形スケーリング（min=0, max=255）  ← デフォルト
     bitshift   : 12bit→8bit ビットシフト (>> 4)
     percentile : 2-98パーセンタイルクリップ後スケーリング
     none       : スケーリングなし（単純コピー）

6. メタデータJSONを指定（撮影日時 NITF_IDATIM を埋め込み）:
   $ python _run_on_runpod/prepare_satellite_sfm_inputs.py \
       --tif_dir /path/to/tifs \
       --output_dir /path/to/inputs \
       --metadata_json /path/to/*_metadata.json

   省略時は tif_dir 内の *_metadata.json を自動検索します。

7. コピーの代わりにシンボリックリンクを使用（ディスク節約、スケーリング無効）:
   $ python _run_on_runpod/prepare_satellite_sfm_inputs.py \
       --tif_dir /path/to/tifs \
       --output_dir /path/to/inputs \
       --symlink

8. 準備完了後、satellite_sfm.py を実行:
   $ python satellite_sfm.py \
       --input_folder <output_dir> \
       --output_folder <output_dir>/../outputs \
       --run_sfm --enable_debug
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np
from osgeo import gdal, gdalconst


def find_tif_files(tif_dir, pattern):
    """TIFファイルを検索して返す。"""
    tif_files = sorted(glob.glob(os.path.join(tif_dir, pattern)))
    if not tif_files:
        print(f"ERROR: No TIF files matching '{pattern}' in {tif_dir}")
        sys.exit(1)
    return tif_files


def _iso_to_nitf_idatim(iso_date):
    """
    ISO 8601 日時文字列を NITF IDATIM 形式に変換する。

    例: "2026-01-14T02:39:00.036" → "20260114023900"
    """
    # ISO 8601: YYYY-MM-DDTHH:MM:SS[.fff]
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", iso_date)
    if not m:
        return None
    return "".join(m.groups())  # "YYYYMMDDHHmmss"


def load_acquisition_dates(metadata_json_path):
    """
    BlackSky メタデータ JSON から各画像の撮影日時を読み込み、
    画像ID → NITF_IDATIM 形式の辞書を返す。

    Args:
        metadata_json_path: *_metadata.json のパス

    Returns:
        dict: {image_id: nitf_idatim_string}
              例: {"BSG-117-20260114-023900-417077014": "20260114023900", ...}
    """
    with open(metadata_json_path, "r") as f:
        data = json.load(f)

    date_map = {}

    # メイン画像
    main_id = data.get("id", "")
    main_date = data.get("acquisitionDate", "")
    if main_id and main_date:
        nitf = _iso_to_nitf_idatim(main_date)
        if nitf:
            date_map[main_id] = nitf

    # otherFrames（マルチフレーム画像セット）
    for frame in data.get("otherFrames", []):
        fid = frame.get("id", "")
        fdate = frame.get("acquisitionDate", "")
        if fid and fdate:
            nitf = _iso_to_nitf_idatim(fdate)
            if nitf:
                date_map[fid] = nitf

    return date_map


def find_metadata_jsons(tif_dir):
    """
    tif_dir 内の *_metadata.json を全て検索して返す。

    Returns:
        見つかったパスのリスト（空リストの場合もあり）
    """
    return sorted(glob.glob(os.path.join(tif_dir, "*_metadata.json")))


def _match_tif_to_date(tif_basename, date_map):
    """
    TIFファイル名から画像IDをマッチさせてNITF_IDATIMを返す。

    例: "BSG-117-20260114-023900-417077014_georeferenced.tif"
        → ID "BSG-117-20260114-023900-417077014" にマッチ
    """
    for image_id, nitf_idatim in date_map.items():
        if tif_basename.startswith(image_id):
            return nitf_idatim
    return None


def scale_uint16_to_uint8(img, method="linear"):
    """
    uint16 画像を uint8 にスケーリングする。

    Args:
        img: numpy array (uint16 or uint8)
        method: スケーリング方式
            - 'linear'    : 線形スケーリング (0→0, max→255)
            - 'bitshift'  : 12bit→8bit ビット右シフト (>> 4)
            - 'percentile': 2-98パーセンタイルクリップ後に線形スケーリング

    Returns:
        uint8 numpy array
    """
    if img.dtype == np.uint8:
        return img

    if method == "linear":
        img_max = img.max()
        if img_max == 0:
            return np.zeros(img.shape, dtype=np.uint8)
        return (img.astype(np.float32) / img_max * 255.0).astype(np.uint8)

    elif method == "bitshift":
        # 12bit (0-4095) → 8bit (0-255)
        return (img >> 4).astype(np.uint8)

    elif method == "percentile":
        p_low, p_high = np.percentile(img, [2, 98])
        if p_high <= p_low:
            return np.zeros(img.shape, dtype=np.uint8)
        clipped = np.clip(img.astype(np.float32), p_low, p_high)
        return ((clipped - p_low) / (p_high - p_low) * 255.0).astype(np.uint8)

    else:
        raise ValueError(f"Unknown scale method: {method}")


def convert_tif_to_uint8(src_path, dst_path, scale_method, nitf_idatim=None):
    """
    TIFファイルを読み込み、uint8にスケーリングして書き出す。
    RPC メタデータなど全メタデータを保持する。
    nitf_idatim が指定された場合、NITF_IDATIM としてメタデータに埋め込む。

    Args:
        src_path: 入力TIFパス
        dst_path: 出力TIFパス
        scale_method: スケーリング方式 ('linear', 'bitshift', 'percentile')
        nitf_idatim: NITF IDATIM 形式の日時文字列（例: '20260114023900'）
    """
    src_ds = gdal.Open(src_path, gdal.GA_ReadOnly)
    if src_ds is None:
        raise RuntimeError(f"Cannot open {src_path}")

    img = src_ds.ReadAsArray()  # shape: (bands, H, W)
    original_dtype = img.dtype

    if original_dtype == np.uint8:
        # 既にuint8 → 単純コピー
        src_ds = None
        shutil.copy2(src_path, dst_path)
        return "COPY (already uint8)"

    # スケーリング実行
    img_scaled = scale_uint16_to_uint8(img, method=scale_method)

    # 出力TIFを作成（GeoTIFF, uint8）
    driver = gdal.GetDriverByName("GTiff")
    bands = img_scaled.shape[0] if len(img_scaled.shape) == 3 else 1
    if len(img_scaled.shape) == 3:
        h, w = img_scaled.shape[1], img_scaled.shape[2]
    else:
        h, w = img_scaled.shape[0], img_scaled.shape[1]

    dst_ds = driver.Create(dst_path, w, h, bands, gdalconst.GDT_Byte)
    if dst_ds is None:
        raise RuntimeError(f"Cannot create {dst_path}")

    # GeoTransform をコピー
    geo_transform = src_ds.GetGeoTransform()
    if geo_transform:
        dst_ds.SetGeoTransform(geo_transform)

    # 投影情報をコピー
    projection = src_ds.GetProjection()
    if projection:
        dst_ds.SetProjection(projection)

    # 全メタデータドメインをコピー（RPC含む）
    for domain in ["", "RPC", "IMAGERY", "NITF_METADATA"]:
        md = src_ds.GetMetadata(domain)
        if md:
            dst_ds.SetMetadata(md, domain)

    # NITF_IDATIM を埋め込み（メタデータJSONから取得した撮影日時）
    if nitf_idatim:
        md_default = dst_ds.GetMetadata() or {}
        md_default["NITF_IDATIM"] = nitf_idatim
        dst_ds.SetMetadata(md_default)

    # バンドデータを書き込み
    if len(img_scaled.shape) == 3:
        for b in range(bands):
            dst_ds.GetRasterBand(b + 1).WriteArray(img_scaled[b])
    else:
        dst_ds.GetRasterBand(1).WriteArray(img_scaled)

    dst_ds.FlushCache()
    dst_ds = None
    src_ds = None

    return f"SCALED ({original_dtype}→uint8, {scale_method})"


def copy_tifs_to_images_dir(tif_files, images_dir, use_symlink=False, scale_method="linear", date_map=None):
    """
    TIFファイルを images/ ディレクトリにスケーリング変換してコピーする。
    uint16 等の画像は uint8 にスケーリングし、RPC メタデータを保持する。
    date_map が与えられた場合、NITF_IDATIM メタデータを埋め込む。
    symlink モードの場合はスケーリングせずリンクのみ作成する。

    Args:
        tif_files: TIFファイルパスのリスト
        images_dir: 出力先ディレクトリ
        use_symlink: Trueの場合シンボリックリンク（スケーリング無効）
        scale_method: スケーリング方式 ('linear', 'bitshift', 'percentile', 'none')
        date_map: {image_id: nitf_idatim} の辞書（Noneの場合は埋め込まない）

    Returns:
        処理されたファイル数
    """
    os.makedirs(images_dir, exist_ok=True)
    if date_map is None:
        date_map = {}

    count = 0
    for src in tif_files:
        basename = os.path.basename(src)
        dst = os.path.join(images_dir, basename)
        if os.path.exists(dst):
            print(f"  SKIP (exists): {basename}")
            continue

        nitf_idatim = _match_tif_to_date(basename, date_map)

        if use_symlink:
            os.symlink(os.path.abspath(src), dst)
            print(f"  LINK: {basename}")
        elif scale_method == "none":
            shutil.copy2(src, dst)
            # symlink/none でも NITF_IDATIM を埋め込む
            if nitf_idatim:
                _embed_nitf_idatim(dst, nitf_idatim)
            print(f"  COPY: {basename}" + (f" (+NITF_IDATIM={nitf_idatim})" if nitf_idatim else ""))
        else:
            action = convert_tif_to_uint8(src, dst, scale_method, nitf_idatim=nitf_idatim)
            extra = f" +NITF_IDATIM={nitf_idatim}" if nitf_idatim else ""
            print(f"  {action}{extra}: {basename}")
        count += 1

    return count


def _embed_nitf_idatim(tif_path, nitf_idatim):
    """既存のTIFファイルに NITF_IDATIM メタデータを追加する。"""
    ds = gdal.Open(tif_path, gdal.GA_Update)
    if ds is None:
        print(f"  WARNING: Cannot open {tif_path} for metadata update")
        return
    md = ds.GetMetadata() or {}
    md["NITF_IDATIM"] = nitf_idatim
    ds.SetMetadata(md)
    ds.FlushCache()
    ds = None


def create_bbx_json(tif_dir, pattern, output_path, alt_min, alt_max):
    """
    create_latlonalt_bbox_json.py を呼び出して latlonalt_bbx.json を生成する。
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bbx_script = os.path.join(script_dir, "create_latlonalt_bbox_json.py")

    if not os.path.exists(bbx_script):
        print(f"ERROR: {bbx_script} not found")
        sys.exit(1)

    cmd = [
        sys.executable, bbx_script,
        "--tif_dir", tif_dir,
        "--pattern", pattern,
        "--output", output_path,
        "--alt_min", str(alt_min),
        "--alt_max", str(alt_max),
    ]

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print("ERROR: Failed to create latlonalt_bbx.json")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="カスタム衛星画像データを satellite_sfm.py の入力形式に整える"
    )
    parser.add_argument(
        "--tif_dir",
        type=str,
        required=True,
        help="元のTIFファイルが格納されたディレクトリ",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="satellite_sfm.py の --input_folder に渡すディレクトリ",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.tif",
        help="TIFファイル名のglobパターン (default: *.tif)",
    )
    parser.add_argument(
        "--alt_min",
        type=float,
        default=-30,
        help="高度の下限 [m] (default: -30)",
    )
    parser.add_argument(
        "--alt_max",
        type=float,
        default=300,
        help="高度の上限 [m] (default: 300)",
    )
    parser.add_argument(
        "--scale_method",
        type=str,
        choices=["linear", "bitshift", "percentile", "none"],
        default="linear",
        help="uint16→uint8 スケーリング方式 (default: linear). "
             "linear: 線形スケーリング, "
             "bitshift: 12bit→8bit ビットシフト, "
             "percentile: 2-98%%パーセンタイルクリップ後スケーリング, "
             "none: スケーリングなし",
    )
    parser.add_argument(
        "--metadata_json",
        type=str,
        default=None,
        help="BlackSky等のメタデータJSONパス（撮影日時をNITF_IDATIMとして埋め込む）。"
             "省略時はtif_dir内の *_metadata.json を自動検索",
    )
    parser.add_argument(
        "--symlink",
        action="store_true",
        default=False,
        help="コピーの代わりにシンボリックリンクを使用（ディスク節約、スケーリング無効）",
    )
    args = parser.parse_args()

    images_dir = os.path.join(args.output_dir, "images")
    bbx_path = os.path.join(args.output_dir, "latlonalt_bbx.json")

    print("=" * 60)
    print("Preparing satellite_sfm.py inputs")
    print("=" * 60)
    print(f"  Source TIF dir : {args.tif_dir}")
    print(f"  Output dir     : {args.output_dir}")
    print(f"  TIF pattern    : {args.pattern}")
    print(f"  Alt range      : [{args.alt_min}, {args.alt_max}]")
    print(f"  Scale method   : {args.scale_method}")
    print(f"  Copy mode      : {'symlink (scaling disabled)' if args.symlink else 'copy'}")

    # --- メタデータJSON の検索・読み込み ---
    date_map = {}
    if args.metadata_json:
        metadata_jsons = [args.metadata_json]
    else:
        metadata_jsons = find_metadata_jsons(args.tif_dir)
    if metadata_jsons:
        for mj in metadata_jsons:
            if os.path.exists(mj):
                dm = load_acquisition_dates(mj)
                date_map.update(dm)
                print(f"  Metadata JSON  : {mj} ({len(dm)} image(s))")
        print(f"  NITF_IDATIM    : {len(date_map)} image(s) mapped total")
    else:
        print(f"  Metadata JSON  : not found (NITF_IDATIM will not be embedded)")

    if args.symlink and args.scale_method != "none":
        print(f"  WARNING: symlink mode — スケーリングは適用されません")
    print()

    # --- Step 1: TIFファイルをスケーリングして images/ にコピー ---
    print("-" * 60)
    print("Step 1: Scale & copy TIF files to images/")
    print("-" * 60)

    tif_files = find_tif_files(args.tif_dir, args.pattern)
    print(f"Found {len(tif_files)} TIF file(s):")
    copied = copy_tifs_to_images_dir(
        tif_files, images_dir,
        use_symlink=args.symlink,
        scale_method=args.scale_method,
        date_map=date_map,
    )
    print(f"  -> {copied} file(s) processed, "
          f"{len(tif_files) - copied} skipped")
    print()

    # --- Step 2: latlonalt_bbx.json を生成 ---
    print("-" * 60)
    print("Step 2: Generate latlonalt_bbx.json from RPC metadata")
    print("-" * 60)

    create_bbx_json(args.tif_dir, args.pattern, bbx_path, args.alt_min, args.alt_max)
    print()

    # --- 完了 ---
    print("=" * 60)
    print("Done! Input directory is ready.")
    print("=" * 60)
    print()
    print("Generated structure:")
    print(f"  {args.output_dir}/")
    print(f"  ├── images/  ({len(tif_files)} TIF files)")
    print(f"  └── latlonalt_bbx.json")
    print()
    print("Next step - run satellite_sfm.py:")
    print(f"  python satellite_sfm.py \\")
    print(f"    --input_folder {args.output_dir} \\")
    print(f"    --output_folder {os.path.join(os.path.dirname(args.output_dir), 'outputs')} \\")
    print(f"    --run_sfm --enable_debug")


if __name__ == "__main__":
    main()
