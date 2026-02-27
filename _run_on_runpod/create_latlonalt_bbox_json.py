#!/usr/bin/env python3
"""
TIFファイルに埋め込まれたRPCメタデータから latlonalt_bbx.json を生成するスクリプト。

satellite_sfm.py の入力として必要な latlonalt_bbx.json を、
GeoTIFF内のRPC情報（LAT_OFF/SCALE, LONG_OFF/SCALE）から自動計算します。

高度範囲(alt_minmax)はRPCの正規化範囲ではなく、対象エリアの実地表高度に基づいて
手動で指定します（デフォルト: [-30, 300]）。

=== 使い方 ===

1. conda環境をアクティベート:
   $ conda activate SatelliteSfM

2. 基本的な使い方（TIFが入ったディレクトリを指定）:
   $ python _run_on_runpod/create_latlonalt_bbox_json.py \
       --tif_dir data/BSG-STEREO-MF-117-20260114-023900-417077014/BSG-STEREO-MF-117-20260114-023900-417077014

3. 出力先を指定:
   $ python _run_on_runpod/create_latlonalt_bbox_json.py \
       --tif_dir data/BSG-STEREO-MF-117-20260114-023900-417077014/BSG-STEREO-MF-117-20260114-023900-417077014 \
       --output data/BSG-STEREO-MF-117-20260114-023900-417077014/inputs/latlonalt_bbx.json

4. 高度範囲を手動指定:
   $ python _run_on_runpod/create_latlonalt_bbox_json.py \
       --tif_dir /path/to/tifs \
       --alt_min -30 --alt_max 300

5. TIFファイル名のパターンを指定（デフォルト: *.tif）:
   $ python _run_on_runpod/create_latlonalt_bbox_json.py \
       --tif_dir /path/to/tifs \
       --pattern "*_georeferenced.tif"

=== 出力例 ===

{
  "lat_minmax": [35.6449, 35.7161],
  "lon_minmax": [139.7247, 139.8013],
  "alt_minmax": [-30, 300]
}
"""

import argparse
import glob
import json
import os
import sys


def extract_rpc_bounds(tif_path):
    """
    TIFファイルのRPCメタデータから緯度・経度・高度の範囲を抽出する。

    RPCメタデータには以下が含まれる:
      - LAT_OFF / LAT_SCALE: 緯度のオフセットとスケール
      - LONG_OFF / LONG_SCALE: 経度のオフセットとスケール
      - HEIGHT_OFF / HEIGHT_SCALE: 高度のオフセットとスケール

    RPCの正規化範囲は [OFF - SCALE, OFF + SCALE] で表される。

    Returns:
        dict: lat_min, lat_max, lon_min, lon_max, alt_min, alt_max
    """
    from osgeo import gdal

    ds = gdal.Open(tif_path)
    if ds is None:
        raise RuntimeError(f"Cannot open: {tif_path}")

    rpc = ds.GetMetadata("RPC")
    if not rpc:
        raise RuntimeError(f"No RPC metadata found in: {tif_path}")

    # "35.6805 degrees" のような文字列から数値だけ取り出す
    lat_off = float(rpc["LAT_OFF"].split()[0])
    lat_scale = float(rpc["LAT_SCALE"].split()[0])
    lon_off = float(rpc["LONG_OFF"].split()[0])
    lon_scale = float(rpc["LONG_SCALE"].split()[0])
    h_off = float(rpc["HEIGHT_OFF"].split()[0])
    h_scale = float(rpc["HEIGHT_SCALE"].split()[0])

    ds = None

    return {
        "lat_min": lat_off - lat_scale,
        "lat_max": lat_off + lat_scale,
        "lon_min": lon_off - lon_scale,
        "lon_max": lon_off + lon_scale,
        "alt_min": h_off - h_scale,
        "alt_max": h_off + h_scale,
    }


def main():
    parser = argparse.ArgumentParser(
        description="TIFのRPCメタデータから latlonalt_bbx.json を生成"
    )
    parser.add_argument(
        "--tif_dir",
        type=str,
        required=True,
        help="TIFファイルが格納されたディレクトリ",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.tif",
        help="TIFファイル名のglobパターン (default: *.tif)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="出力先パス (default: <tif_dir>/latlonalt_bbx.json)",
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
    args = parser.parse_args()

    # TIFファイルを検索
    tif_files = sorted(glob.glob(os.path.join(args.tif_dir, args.pattern)))
    if not tif_files:
        print(f"ERROR: No TIF files matching '{args.pattern}' in {args.tif_dir}")
        sys.exit(1)

    print(f"Found {len(tif_files)} TIF file(s):")

    # 各TIFからRPC範囲を取得
    all_bounds = []
    for f in tif_files:
        print(f"  {os.path.basename(f)}")
        bounds = extract_rpc_bounds(f)
        print(f"    lat: [{bounds['lat_min']:.6f}, {bounds['lat_max']:.6f}]")
        print(f"    lon: [{bounds['lon_min']:.6f}, {bounds['lon_max']:.6f}]")
        print(f"    alt (RPC range): [{bounds['alt_min']:.1f}, {bounds['alt_max']:.1f}]")
        all_bounds.append(bounds)

    # 全TIFの範囲を統合（外接矩形）
    bbx = {
        "lat_minmax": [
            min(b["lat_min"] for b in all_bounds),
            max(b["lat_max"] for b in all_bounds),
        ],
        "lon_minmax": [
            min(b["lon_min"] for b in all_bounds),
            max(b["lon_max"] for b in all_bounds),
        ],
        "alt_minmax": [args.alt_min, args.alt_max],
    }

    # 出力
    output_path = args.output or os.path.join(args.tif_dir, "latlonalt_bbx.json")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(bbx, f, indent=2)

    print()
    print(f"=== Generated latlonalt_bbx.json ===")
    print(json.dumps(bbx, indent=2))
    print()
    print(f"Saved to: {output_path}")
    print()
    print(f"NOTE: alt_minmax is set to [{args.alt_min}, {args.alt_max}] (manual).")
    print(f"      RPC alt range was [{min(b['alt_min'] for b in all_bounds):.1f}, "
          f"{max(b['alt_max'] for b in all_bounds):.1f}] (not used).")
    print(f"      Adjust --alt_min / --alt_max if needed for your area.")


if __name__ == "__main__":
    main()
