## 1. SatelliteSfM は ColmapForVisSat をどう使っているか

### 1.1 ビルド・導入の入口

SatelliteSfM ルートの `env.sh` にて、以下が最初に実行される：

```bash
bash ./preprocess_sfm/install_colmapforvissat.sh
```

つまり SatelliteSfM は、**ColmapForVisSat をプロジェクト配下でビルドすることを前提**としている。

---

### 1.2 colmap 実行の実体

`preprocess_sfm/colmap_sfm_commands.py` に、colmap 実行ロジックが集中している。

#### colmap バイナリの扱い

- colmap は **CLI バイナリとして呼び出される**（ライブラリリンクではない）
- パスは以下に **ハードコード**されている：

```text
preprocess_sfm/ColmapForVisSat/build/__install__/bin/colmap
```

#### 実行環境

- `LD_LIBRARY_PATH` を

```text
preprocess_sfm/ColmapForVisSat/build/__install__/lib
```

に設定した上で、`/bin/bash -c` 経由でコマンドを実行

---

### 1.3 実行される colmap サブコマンド

Step1 の SfM パイプラインでは、少なくとも以下が使用される：

- `colmap feature_extractor`
- `colmap exhaustive_matcher`
- `colmap point_triangulator`
- `colmap bundle_adjuster`

SatelliteSfM は **GUI (Qt/OpenGL) を一切使わない**。