# _run_on_runpod

このディレクトリには当リポジトリをRunPod上で動かすための情報を記述します。

SatelliteSfMはUbuntu 18.04で動くことを前提としている。
一方でRunPodの仮想マシンテンプレートではUbuntu 18系の環境を入手できないため、
Ubuntu22.04 + CUDA11.8
のテンプレート（下記）を使用してその環境で動くように元リポジトリに手を入れていく方針で環境構築します。

```
runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04
```

## リポジトリ情報

- SatelliteSfM:
RPC形式の衛星画像をSkyfallGSS形式に変換するためのリポジトリ。
- ColmapForVisSat:
Colmapを衛星画像に特化して改造したリポジトリ。
このリポジトリをビルドしたColmapをSatelliteSfMから呼び出して使用する。

## 作業対象のリポジトリ・ブランチ

RunPod上で動かすため、オリジナルのリポジトリを下記のリポジトリにforkした。
forkしたリポジトリの「run_on_runpod」ブランチを作業対象とする。

https://github.com/HikosakaRyo/SatelliteSfM

https://github.com/HikosakaRyo/ColmapForVisSat

## ColmapForVisSatとの連携

「ColmapForVisSat.md」を参照

## 環境構築の計画概要

詳細は調査しながら進める必要があるが、大まかな方針は以下のとおりとする。

### ColmapForVisSatのビルドを通す

本リポジトリの
```bash
bash ./preprocess_sfm/install_colmapforvissat.sh
```

が成功するように本リポジトリのinstall_colmapforvissat.shを編集する。
※ColmapForVisSatのコードも修正が必要な可能性も考慮してクローン元のリポジトリは
https://github.com/HikosakaRyo/ColmapForVisSat
の「run_on_runpod」ブランチに変更してある。

install_colmapforvissat.shではGCC/G++のバージョンが7固定になっているが、Ubuntu22.04の環境ではGCC/G++のバージョンが11になるため、これを11に変更する必要がある。
また、gccなどのビルドツールがインストールされていない可能性もあるため、必要に応じてビルドツールのインストールも行う必要がある。
インストールが必要なツールがある場合は、_run_on_runpod/install_build_tools.shを作成してそこにインストールコマンドをまとめる方針とする。

### SatelliteSfMのビルドを通す

ColmapForVisSatのビルドが通った後、SatelliteSfMのビルドも通す必要がある。
env.shの実行が最後まで成功するように修正を加える必要がある。
env.shの修正に加え、インストールに必要なツール（condaなど）が不足している可能性もあるため、必要に応じて_build_tools/install_build_tools.shにインストールコマンドを追加する方針とする。

## 実行順序

RunPod インスタンス上で環境構築を行う際は、以下の順序でコマンドを実行する。

### 1. ビルドツールのインストール

```bash
bash _run_on_runpod/install_build_tools.sh
```

このスクリプトは以下をインストールする：
- 基本ビルドツール (build-essential, cmake, ninja-build, etc.)
- ColmapForVisSat 依存ライブラリ (Boost, Eigen, Ceres, CGAL, etc.)
- Qt5 関連 (ビルド互換性のため)
- SatelliteSfM 追加依存ライブラリ (libcurl, libgl1-mesa-glx)
- **Miniconda** (Python 環境管理用)

**重要**: スクリプト実行後、conda を有効化するために以下を実行：
```bash
source ~/.bashrc
```

### 2. ColmapForVisSat のビルド

```bash
bash ./preprocess_sfm/install_colmapforvissat.sh
```

成功すると `preprocess_sfm/ColmapForVisSat/build/__install__/bin/colmap` が生成される。

### 3. SatelliteSfM 環境セットアップ

**重要**: `bash` ではなく `source` で実行すること（conda activate のため）

```bash
source ./env.sh
```

成功すると以下が完了する：
- conda 環境 `SatelliteSfM` の作成（Python 3.8）
- 必要な Python パッケージのインストール（numpy, opencv, gdal, srtm4, etc.）

### 4. 検証

環境セットアップ後、以下のコマンドで動作確認：

```bash
conda activate SatelliteSfM
python -c "from osgeo import gdal; print('GDAL:', gdal.__version__)"
python -c "import srtm4; print('srtm4: OK')"
python satellite_sfm.py --help
```

## トラブルシューティング

### gcc/g++ が見つからない場合

```
ERROR: C/C++ compiler not found.cd 
```

このエラーが出た場合は、先に `install_build_tools.sh` を実行してください：

```bash
bash _run_on_runpod/install_build_tools.sh
```

### ColmapForVisSat のビルドが失敗する場合

1. ビルドログを確認：
   ```bash
   cat preprocess_sfm/ColmapForVisSat/build_log.txt
   ```

2. 依存ライブラリが不足している場合は、エラーメッセージに基づいて `install_build_tools.sh` に追記してください。

3. CUDA 関連のエラーの場合：
   ```bash
   nvcc --version  # CUDA コンパイラが利用可能か確認
   echo $CUDA_HOME # CUDA パスが設定されているか確認
   ```

### colmap バイナリが見つからない場合

ビルド成功後、以下のパスに `colmap` が存在するか確認：

```bash
ls -la preprocess_sfm/ColmapForVisSat/build/__install__/bin/colmap
```

存在しない場合は、ビルドログを確認して原因を特定してください。

### conda が見つからない場合

```
ERROR: conda not found!
```

1. `install_build_tools.sh` を実行したか確認
2. 実行後、新しいシェルを開くか `source ~/.bashrc` を実行

```bash
source ~/.bashrc
conda --version
```

### env.sh が失敗する場合

1. `source` で実行しているか確認（`bash ./env.sh` ではなく）：
   ```bash
   source ./env.sh
   ```

2. conda 環境が壊れている場合は削除して再作成：
   ```bash
   conda env remove -n SatelliteSfM
   source ./env.sh
   ```

3. GDAL インストールが失敗する場合：
   ```bash
   conda install -y -c conda-forge gdal
   ```

### Open3D のインポートエラー

ヘッドレス環境で Open3D を使用する際のエラー：

```bash
# libGL エラーの場合
apt-get install -y libgl1-mesa-glx

# DISPLAY 関連のエラーの場合（可視化機能を使用しない場合は無視可能）
```

