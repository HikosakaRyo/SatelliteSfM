#!/usr/bin/env bash
# ==============================================================================
# install_build_tools.sh
# ColmapForVisSat および SatelliteSfM のビルドに必要なツール・依存パッケージを
# Ubuntu 22.04 環境にインストールするスクリプト
# ==============================================================================
set -e

echo "=========================================="
echo "Installing build tools and dependencies"
echo "=========================================="

# パッケージリストを更新
apt-get update

# ==============================================================================
# 基本ビルドツール
# ==============================================================================
echo "Installing basic build tools..."
apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    pkg-config \
    git \
    wget \
    curl

# ==============================================================================
# Python 開発ヘッダー
# ==============================================================================
echo "Installing Python development headers..."
apt-get install -y \
    python3-dev \
    python3-pip

# ==============================================================================
# ColmapForVisSat 依存ライブラリ (CLI ビルド用最小構成)
# ==============================================================================
echo "Installing ColmapForVisSat dependencies..."
apt-get install -y \
    libboost-all-dev \
    libeigen3-dev \
    libflann-dev \
    libfreeimage-dev \
    libmetis-dev \
    libgoogle-glog-dev \
    libgflags-dev \
    libsqlite3-dev \
    libglew-dev \
    libcgal-dev

# ==============================================================================
# Ceres Solver 依存
# ==============================================================================
echo "Installing Ceres Solver dependencies..."
apt-get install -y \
    libatlas-base-dev \
    libsuitesparse-dev \
    libceres-dev

# ==============================================================================
# Qt5 関連 (COLMAP ビルドに必要な場合あり)
# GUI は使用しないが、ビルド時に必要となる可能性があるため含める
# ==============================================================================
echo "Installing Qt5 dependencies (for build compatibility)..."
apt-get install -y \
    qtbase5-dev \
    libqt5opengl5-dev

# ==============================================================================
# SatelliteSfM 追加依存ライブラリ
# ==============================================================================
echo "Installing additional libraries for SatelliteSfM..."
apt-get install -y \
    libcurl4-openssl-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libtiff-dev

# ==============================================================================
# CUDA 関連の確認
# ==============================================================================
echo "Checking CUDA availability..."
if command -v nvcc &> /dev/null; then
    echo "CUDA compiler (nvcc) found: $(nvcc --version | grep release)"
else
    echo "WARNING: nvcc not found. CUDA support may not be available."
    echo "If CUDA is required, ensure CUDA toolkit is installed."
fi

# ==============================================================================
# インストール完了
# ==============================================================================
echo "=========================================="
echo "Build tools installation completed!"
echo "=========================================="

# バージョン確認
echo ""
echo "Installed versions:"
echo "  GCC: $(gcc --version | head -n1)"
echo "  G++: $(g++ --version | head -n1)"
echo "  CMake: $(cmake --version | head -n1)"
echo "  Python3: $(python3 --version)"

# ==============================================================================
# Miniconda のインストール
# ==============================================================================
echo ""
echo "=========================================="
echo "Installing Miniconda..."
echo "=========================================="

MINICONDA_DIR="/root/miniconda3"

if [ -d "$MINICONDA_DIR" ]; then
    echo "Miniconda already installed at $MINICONDA_DIR, skipping..."
else
    echo "Downloading Miniconda installer..."
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
    
    echo "Installing Miniconda to $MINICONDA_DIR..."
    bash /tmp/miniconda.sh -b -p "$MINICONDA_DIR"
    rm /tmp/miniconda.sh
    
    echo "Initializing conda for bash..."
    "$MINICONDA_DIR/bin/conda" init bash
    
    echo "Miniconda installation completed!"
fi

# conda を現在のシェルで使用可能にする
eval "$($MINICONDA_DIR/bin/conda shell.bash hook)"

echo ""
echo "Conda version: $(conda --version)"

# ==============================================================================
# Conda Terms of Service への同意
# ==============================================================================
echo ""
echo "Accepting Conda Terms of Service..."
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main || true
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r || true
echo "Conda ToS accepted."

# ==============================================================================
# インストール完了
# ==============================================================================
echo ""
echo "=========================================="
echo "All installations completed!"
echo "=========================================="
echo ""
echo "IMPORTANT: Run 'source ~/.bashrc' to enable conda in your current shell."
echo ""
echo "Next steps:"
echo "  1. Run: source ~/.bashrc"
echo "  2. Run: bash ./preprocess_sfm/install_colmapforvissat.sh  (if not done)"
echo "  3. Run: source ./env.sh"
