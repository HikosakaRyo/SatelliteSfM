# ColmapForVisSat のビルド通過に向けた実装計画（Ubuntu22.04 + CUDA11.8）

## 背景
- `env.sh` から `preprocess_sfm/install_colmapforvissat.sh` が最初に呼ばれるため、ここが通らないと後続の環境構築に進めない。
- 現在の `install_colmapforvissat.sh` は `gcc-7/g++-7` 前提で、Ubuntu22.04 の標準構成（gcc-11系）と不整合。
- さらに、ColmapForVisSat の clone 元 URL が誤っており、実際には ColmapForVisSat を取得できない。

## 実装方針

### 1. `install_colmapforvissat.sh` の取得元と前提チェックを修正
1. clone 元を `HikosakaRyo/ColmapForVisSat` の `run_on_runpod` ブランチへ修正。
2. C/C++ コンパイラの決定ロジックを以下へ変更。
   - 優先: `/usr/bin/gcc-11`, `/usr/bin/g++-11`
   - 次点: `gcc`, `g++`（`command -v` で存在確認）
   - 見つからない場合のみエラー終了。
3. ハードコードされた `CC=/usr/bin/gcc-7 CXX=/usr/bin/g++-7` を、上記判定結果を使う実装へ置換。

### 2. ビルドツール導入スクリプトを新設（必要時のみ）
README 方針に合わせ `_run_on_runpod/install_build_tools.sh` を追加し、下記を一括導入可能にする。
- `build-essential`
- `cmake`
- `ninja-build`
- `pkg-config`
- `git`
- `python3-dev`
- （ColmapForVisSat 側の依存不足が出たものを追記）

> 備考: GUI は使わないため、Qt 実行用途の依存は優先度低。CLI ビルドに必要な最小集合から始める。

### 3. 実行順序の明確化
- RunPod 初期セットアップ手順を以下に統一。
  1. `_run_on_runpod/install_build_tools.sh`
  2. `bash ./preprocess_sfm/install_colmapforvissat.sh`
  3. `bash ./env.sh` の残り工程

### 4. 検証項目（DoD）
1. `preprocess_sfm/install_colmapforvissat.sh` が終了コード 0。
2. `preprocess_sfm/ColmapForVisSat/build/__install__/bin/colmap` が生成される。
3. `preprocess_sfm/colmap_sfm_commands.py` の想定パスで `colmap` 実行可能（`colmap -h` 等）。
4. ビルドログ（`build_log.txt`）に致命エラーが残らない。

## 実装タスク分解
1. `install_colmapforvissat.sh` 修正（clone URL / compiler 判定 / エラーメッセージ）。
2. `_run_on_runpod/install_build_tools.sh` 新規作成。
3. `_run_on_runpod/README.md` に実行順序とトラブルシュート（gcc未検出時）を追記。
4. RunPod テンプレートで実行し、ログ付きで検証結果を記録。

## リスクと対策
- **リスク:** ColmapForVisSat 側で Ubuntu22.04 非互換 API/依存が露出。
  - **対策:** まずは install script 側で解決できる依存不足を潰し、残件は ColmapForVisSat `run_on_runpod` ブランチに最小修正を当てる。
- **リスク:** CUDA/コンパイラ組合せ起因の CMake 検出失敗。
  - **対策:** `CC/CXX` の明示 + CMake ログを保存して分岐対応。
