#!/usr/bin/env bash
set -e

cur_dir=$(pwd)
work_dir=$(dirname "$0")
cd "$work_dir"

# ==============================================================================
# コンパイラ検出ロジック
# 優先: gcc-11/g++-11 → 次点: gcc/g++ → 見つからない場合はエラー
# ==============================================================================
detect_compiler() {
    local cc_cmd=""
    local cxx_cmd=""

    # 優先: gcc-11/g++-11
    if [[ -f "/usr/bin/gcc-11" ]] && [[ -f "/usr/bin/g++-11" ]]; then
        cc_cmd="/usr/bin/gcc-11"
        cxx_cmd="/usr/bin/g++-11"
        echo "INFO: Using gcc-11/g++-11"
    # 次点: システムの gcc/g++
    elif command -v gcc &> /dev/null && command -v g++ &> /dev/null; then
        cc_cmd=$(command -v gcc)
        cxx_cmd=$(command -v g++)
        echo "INFO: Using system gcc/g++ at $cc_cmd / $cxx_cmd"
    else
        echo "ERROR: C/C++ compiler not found."
        echo "Please install build-essential or gcc/g++ and try again."
        echo "You can run: bash _run_on_runpod/install_build_tools.sh"
        exit 1
    fi

    # バージョン確認
    echo "CC version: $($cc_cmd --version | head -n1)"
    echo "CXX version: $($cxx_cmd --version | head -n1)"

    export CC="$cc_cmd"
    export CXX="$cxx_cmd"
}

detect_compiler

# ==============================================================================
# ColmapForVisSat のクローン
# ==============================================================================
if [[ ! -d "ColmapForVisSat" ]]; then
    echo "INFO: Cloning ColmapForVisSat repository..."
    git clone -b run_on_runpod https://github.com/HikosakaRyo/ColmapForVisSat.git
else
    echo "INFO: ColmapForVisSat directory already exists, skipping clone."
fi

# ==============================================================================
# Note: FreeImage の C++14 対応は build.py 内で Makefile.gnu を編集する形で
# 実装されています（CXXFLAGS に -std=c++14 を追加）
# ==============================================================================

# ==============================================================================
# 既存のビルドディレクトリをクリーンアップ（失敗したビルドのリトライ用）
# ==============================================================================
if [[ -d "ColmapForVisSat/build/freeimage" ]] && [[ ! -f "ColmapForVisSat/build/freeimage/libfreeimage.a" ]]; then
    echo "INFO: Removing incomplete freeimage build directory..."
    rm -rf "ColmapForVisSat/build/freeimage"
fi

# ==============================================================================
# ビルド実行
# ==============================================================================
echo "INFO: Starting ColmapForVisSat build with CC=$CC CXX=$CXX"
CC="$CC" CXX="$CXX" \
    python3 ColmapForVisSat/scripts/python/build.py \
        --build_path ColmapForVisSat/build \
        --colmap_path ColmapForVisSat 2>&1 | tee ColmapForVisSat/build_log.txt

build_exit_code=${PIPESTATUS[0]}

if [[ $build_exit_code -eq 0 ]]; then
    echo "INFO: Build completed successfully."
    # 生成物の確認
    if [[ -f "ColmapForVisSat/build/__install__/bin/colmap" ]]; then
        echo "INFO: colmap binary found at ColmapForVisSat/build/__install__/bin/colmap"
    else
        echo "WARNING: colmap binary not found at expected path."
    fi
else
    echo "ERROR: Build failed with exit code $build_exit_code"
    echo "Please check ColmapForVisSat/build_log.txt for details."
fi

cd "$cur_dir"
exit $build_exit_code
