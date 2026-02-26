# SatelliteSfM 環境構築 実装記録

本ドキュメントは `SatelliteSfM_build_plan.md` に基づいて実施した修正内容を記録したものです。

## 実施日

2026-02-26

## 実施内容

### 1. `_run_on_runpod/install_build_tools.sh` の修正

#### 修正内容

1. **Miniconda のインストール追加**
   - Miniconda インストーラーをダウンロード
   - `/root/miniconda3` にインストール
   - `conda init bash` で初期化

2. **追加ライブラリのインストール**
   - `libcurl4-openssl-dev` - srtm4 がデータダウンロードに使用
   - `libgl1-mesa-glx` - Open3D/OpenCV のヘッドレス実行に必要

### 2. `env.sh` の修正

#### 修正前の問題点

1. **conda コマンドが利用不可**: RunPod 環境には conda が未インストール
2. **conda activate がスクリプト内で動作しない**: `eval "$(conda shell.bash hook)"` が必要
3. **不足パッケージ**: scipy, pillow, tifffile, numpy_groupies が env.sh に記載なし
4. **エラーハンドリングなし**: 失敗時の原因特定が困難

#### 修正内容

1. **エラーハンドリング追加**
   - `set -e` でエラー時即座に終了
   - 各ステップのログ出力

2. **conda 初期化処理追加**
   - `eval "$(conda shell.bash hook)"` でスクリプト内から conda activate を可能に

3. **conda 利用可能性チェック**
   - conda が見つからない場合のエラーメッセージと対処法を表示

4. **環境作成の冪等性確保**
   - 既存環境がある場合はスキップ

5. **不足パッケージの追加**
   - `scipy`
   - `pillow`
   - `tifffile`
   - `numpy_groupies`

### 3. `_run_on_runpod/README.md` の更新

実行手順に `source ~/.bashrc` の必要性を追記。

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `_run_on_runpod/install_build_tools.sh` | Miniconda インストール追加、追加ライブラリ |
| `env.sh` | エラーハンドリング、conda 初期化、不足パッケージ追加 |
| `_run_on_runpod/README.md` | 実行手順更新 |
| `_run_on_runpod/SatelliteSfM_build_plan.md` | 計画ドキュメント（新規作成） |
| `_run_on_runpod/SatelliteSfM_implementation_log.md` | 本ドキュメント（新規作成） |

## 検証項目 (DoD)

`SatelliteSfM_build_plan.md` に記載の検証項目:

- [ ] `bash _run_on_runpod/install_build_tools.sh` が終了コード 0 で完了
- [ ] `source ./env.sh` が終了コード 0 で完了
- [ ] `conda activate SatelliteSfM` が成功
- [ ] 主要パッケージのインポートが成功（gdal, srtm4, scipy, open3d, PIL）
- [ ] `python satellite_sfm.py --help` が実行可能

## 発生した問題と対処

### 問題1: `set -e` による source 実行時のターミナル終了

**症状**: `source ./env.sh` 実行時にターミナル自体が閉じてしまう

**原因**: 
- `set -e` があると、コマンドが失敗した時点で `exit 1` が実行される
- `source` で実行すると、スクリプト内の `exit` は現在のシェル（ターミナル自体）を終了させる

**対処**: 
- `env.sh` から `set -e` を削除
- 代わりにログファイル出力を追加（`/tmp/env_setup_*.log`）

### 問題2: Conda Terms of Service (ToS) への同意が必要

**症状**: 
```
CondaToSNonInteractiveError: Terms of Service have not been accepted for the following channels.
```

**原因**: Miniconda 25.x 以降、Anaconda チャンネルの使用には ToS への同意が必要

**対処**: `install_build_tools.sh` に以下を追加
```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

### 問題3: conda 環境が作成されず Python 3.13 で実行された

**症状**: 
- `open3d` インストール失敗（Python 3.13 用ビルドが存在しない）
- 意図した Python 3.8 環境ではなく base 環境（Python 3.13）で pip install が実行された

**原因**: ToS 問題で `conda create` が失敗したが、スクリプトは続行した

**対処**: ToS 問題を解決後、環境を再作成

### 問題4: srtm4 ビルド失敗（libtiff-4.pc が見つからない）

**症状**:
```
Package libtiff-4 was not found in the pkg-config search path.
src/srtm4.c:9:10: fatal error: tiffio.h: No such file or directory
```

**原因**: `libtiff-dev` パッケージが未インストール

**対処**: `install_build_tools.sh` に `libtiff-dev` を追加

## 今後の課題

（実行後に判明した課題があれば、ここに記録）
