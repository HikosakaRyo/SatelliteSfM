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



