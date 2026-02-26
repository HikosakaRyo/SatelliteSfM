# SatelliteSfM 環境構築計画

本ドキュメントは RunPod (Ubuntu 22.04 + CUDA 11.8) 上で SatelliteSfM の環境構築（`env.sh` の実行成功）を行うための計画です。

## 背景

- **前提条件**: ColmapForVisSat のビルドは完了済み（`_run_on_runpod/ColmapForVisSat_implementation_log.md` 参照）
- **目標**: `env.sh` が最後まで成功するように修正を加える
- **環境**: RunPod テンプレート `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04`

## 現状分析

### env.sh の処理内容

現行の `env.sh` は以下を実行する:

1. conda 環境 `SatelliteSfM` を Python 3.8 で作成
2. pip パッケージのインストール（numpy, matplotlib, opencv-python, pyexr, open3d, tqdm, icecream, imageio, imageio-ffmpeg, utm, pyproj, pymap3d, trimesh, pyquaternion）
3. conda-forge から gdal をインストール
4. anaconda から libtiff をインストール、環境変数を設定
5. srtm4 を pip でインストール

### 問題点

| 問題 | 影響 | 対応方針 |
|------|------|---------|
| conda が未インストール | env.sh の冒頭で失敗 | Miniconda をインストール |
| `conda activate` がサブシェルで動作しない | 環境切り替え失敗 | `source` 経由で実行、または `eval "$(conda shell.bash hook)"` を使用 |
| 依存パッケージの不足 | scipy, pillow が env.sh に記載なし | pip install に追加 |
| エラーハンドリングなし | 失敗原因の特定が困難 | `set -e` とログ出力を追加 |

### コードベースで使用されているパッケージ（env.sh に不足）

- `scipy` - `preprocess/approximate_rpc_locally.py`, `preprocess/factorize_projection_matrix.py`
- `pillow` - `generate_masks.py`
- `tifffile` - `preprocess_track3/preprocess_track3.py`
- `numpy_groupies` - `preprocess_track3/preprocess_track3.py`

## 実装計画

### Step 1: install_build_tools.sh に Miniconda インストールを追加

`_run_on_runpod/install_build_tools.sh` に以下を追記:

- Miniconda インストーラーのダウンロード
- `/root/miniconda3` へのインストール
- conda の初期化（`conda init bash`）
- `.bashrc` への conda 初期化スクリプト追加
- srtm4 に必要なシステムライブラリのインストール（`libcurl4-openssl-dev`）
- Open3D/OpenCV に必要なライブラリ（`libgl1-mesa-glx`）

### Step 2: env.sh の修正

修正内容:

1. **エラーハンドリング追加**
   - `set -e` でエラー時に即座に終了
   - 各ステップの開始・終了ログを出力

2. **conda 利用可能性チェック**
   - conda コマンドが見つからない場合のエラーメッセージ

3. **環境作成の冪等性確保**
   - 既存環境がある場合はスキップ、または再作成するかを選択可能に

4. **不足パッケージの追加**
   - `scipy`
   - `pillow`
   - `tifffile`
   - `numpy_groupies`

5. **conda activate の修正**
   - スクリプト内で `conda activate` するには `eval "$(conda shell.bash hook)"` が必要

### Step 3: 検証

以下のコマンドが成功することを確認:

```bash
# 1. ビルドツールとMinicondaのインストール
bash _run_on_runpod/install_build_tools.sh

# 2. 新しいシェルを開く（conda初期化のため）、またはsourceする
source ~/.bashrc

# 3. SatelliteSfM環境のセットアップ
source ./env.sh

# 4. 依存パッケージのインポートテスト
conda activate SatelliteSfM
python -c "from osgeo import gdal; print('GDAL:', gdal.__version__)"
python -c "import srtm4; print('srtm4: OK')"
python -c "import scipy; print('scipy:', scipy.__version__)"
python -c "import open3d; print('Open3D:', open3d.__version__)"
python -c "from PIL import Image; print('Pillow: OK')"
```

## 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `_run_on_runpod/install_build_tools.sh` | Miniconda インストール、追加ライブラリ |
| `env.sh` | エラーハンドリング、不足パッケージ追加、conda activate 修正 |
| `_run_on_runpod/README.md` | 実行手順の更新（source 必須の注記など） |

## 検証項目 (DoD: Definition of Done)

- [ ] `bash _run_on_runpod/install_build_tools.sh` が終了コード 0 で完了
- [ ] `source ./env.sh` が終了コード 0 で完了
- [ ] `conda activate SatelliteSfM` が成功
- [ ] 主要パッケージのインポートが成功（gdal, srtm4, scipy, open3d, PIL）
- [ ] `python satellite_sfm.py --help` が実行可能

## 実装記録

実装を実施する際にやったことすべてを以下のファイルに記録する:

**`_run_on_runpod/SatelliteSfM_implementation_log.md`**

記録内容:
- 実施日時
- 各修正の詳細（変更前後のコード）
- 発生したエラーと対処法
- 検証結果

## リスクと対策

| リスク | 発生可能性 | 対策 |
|--------|-----------|------|
| gdal conda パッケージと Python 3.8 の非互換 | 低 | conda-forge の最新パッケージを使用 |
| Open3D のヘッドレス環境での動作不良 | 中 | `DISPLAY` 環境変数の設定、または headless 版の使用 |
| srtm4 のデータダウンロード失敗 | 低 | libcurl の事前インストール |

## 参考情報

- ColmapForVisSat ビルド記録: `_run_on_runpod/ColmapForVisSat_implementation_log.md`
- RunPod 環境情報: `_run_on_runpod/README.md`
