# note: launch this script via ". ./env.sh" or "source ./env.sh"
# ==============================================================================
# SatelliteSfM 環境セットアップスクリプト
# ==============================================================================
# set -e は source 実行時にターミナルを閉じてしまうため使用しない
# 代わりに各コマンドの戻り値を確認する

# ログファイルにも出力
LOGFILE="/tmp/env_setup_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOGFILE") 2>&1
echo "Log file: $LOGFILE"

echo "=========================================="
echo "Setting up SatelliteSfM environment"
echo "=========================================="

# ColmapForVisSatは単独の手順でビルドする前提としたため、ここではスキップ
# bash ./preprocess_sfm/install_colmapforvissat.sh

# ==============================================================================
# conda の初期化
# ==============================================================================
echo "Initializing conda..."

# conda コマンドが利用可能か確認
if ! command -v conda &> /dev/null; then
    # conda が PATH にない場合、Miniconda のデフォルトパスを試す
    if [ -f "/root/miniconda3/bin/conda" ]; then
        eval "$(/root/miniconda3/bin/conda shell.bash hook)"
    else
        echo "ERROR: conda not found!"
        echo "Please install Miniconda first by running:"
        echo "  bash _run_on_runpod/install_build_tools.sh"
        echo "  source ~/.bashrc"
        echo "Aborting setup (but not closing terminal)."
        return 1 2>/dev/null || true
    fi
else
    # conda activate をスクリプト内で使えるようにする
    eval "$(conda shell.bash hook)"
fi

echo "Conda found: $(conda --version)"

# ==============================================================================
# conda 環境の作成
# ==============================================================================
ENV_NAME="SatelliteSfM"

if conda env list | grep -q "^${ENV_NAME} "; then
    echo "Conda environment '${ENV_NAME}' already exists."
    echo "Activating existing environment..."
else
    echo "Creating conda environment '${ENV_NAME}' with Python 3.8..."
    conda create -y -n ${ENV_NAME} python=3.8
fi

conda activate ${ENV_NAME}
echo "Activated environment: ${ENV_NAME}"

# ==============================================================================
# pip パッケージのインストール
# ==============================================================================
echo ""
echo "Installing pip packages..."
pip install numpy matplotlib opencv-python pyexr open3d tqdm icecream imageio imageio-ffmpeg
pip install utm pyproj pymap3d
pip install trimesh pyquaternion

# 追加パッケージ（コードベースで使用されているが元の env.sh に記載なし）
echo "Installing additional required packages..."
pip install scipy pillow tifffile numpy_groupies

# ==============================================================================
# conda パッケージのインストール
# ==============================================================================
echo ""
echo "Installing GDAL from conda-forge..."
conda install -y -c conda-forge gdal

echo "Installing libtiff from anaconda..."
conda install -y -c anaconda libtiff

# ==============================================================================
# 環境変数の設定
# ==============================================================================
echo ""
echo "Setting environment variables..."
export CPATH=$CONDA_PREFIX/include:$CPATH
export LIBRARY_PATH=$CONDA_PREFIX/lib:$LIBRARY_PATH

# ==============================================================================
# srtm4 のインストール
# ==============================================================================
echo ""
echo "Installing srtm4..."
pip install srtm4

# ==============================================================================
# セットアップ完了
# ==============================================================================
echo ""
echo "=========================================="
echo "SatelliteSfM environment setup completed!"
echo "=========================================="
echo ""
echo "Environment: ${ENV_NAME}"
echo "Python: $(python --version)"
echo ""
echo "To use this environment in a new terminal, run:"
echo "  conda activate ${ENV_NAME}"

