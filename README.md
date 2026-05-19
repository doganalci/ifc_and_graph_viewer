# Erişilebilirlik Dataset Viewer

[codex1](https://github.com/doganalci/codex1) projesinin ürettiği **erişilebilirlik
ihlal havuzu + ihlalli IFC dataset'ini** okuyup inceleyen, Streamlit tabanlı,
**read-only** bir görüntüleyici.

Veri tabanını yazmaz, dosyaları değiştirmez; sadece görselleştirir.

## MVP Özellikler (bu sürüm)

- 🗂️ **Dataset browser** — Tüm baseline / violated / imported IFC'leri filtrele
  (tür, status, havuz, etiket sayısı, isim arama).
- 🧱 **3D viewer** — `ifcopenshell.geom` ile tessellate, plotly Mesh3d.
  Kırmızı = ihlal, sarı = decoy, soluk = normal.
- 🕸️ **Graph viewer** — NetworkX `graph.json`'u plotly 2D olarak çizer
  (pan + scroll zoom).
- 🏷️ **Etiket tablosu + kanıt zinciri** — Her etiket için before/after,
  havuz kaydı, evidence dokümanları.
- 📄 **Meta + dosya indirme** — meta.json, params, prompt; tüm ürün
  dosyalarını indir.
- 📊 **Sidebar özet** — Havuz/IFC/etiket sayıları, toplam token.

## Yol Haritası (sıradaki)

- Çoklu IFC karşılaştırma (2×2 / 3×1 grid)
- Etiket analitiği (kategori/severity/action dağılımı)
- Graph diff (baseline ↔ violated)
- Decoy/gerçek tahmin oyunu
- HuggingFace / Parquet export

## Kurulum

```bash
conda create -n viewer python=3.11 -y
conda activate viewer
pip install -r requirements.txt
# Geometri için (zorunlu):
conda install -c conda-forge ifcopenshell

cp .env.example .env  # VIEWER_DATASET_ROOT=../codex1
streamlit run app.py
```

`VIEWER_DATASET_ROOT` codex1'in kök klasörünü gösterir (içinde
`violation_pool.sqlite` ve `ifc_models/` olmalı). Sol panelden de
çalışırken değiştirilebilir.

## Yapı

```
app.py                 # Streamlit giriş noktası
viewer/
  config.py            # DatasetPaths — dataset kök çözümleme
  db.py                # SQLite read-only sorgular (mode=ro)
  ifc3d.py             # IFC → plotly Mesh3d
  graph_view.py        # graph.json → plotly 2D
```

## Notlar

- Dataset SQLite `mode=ro` URI ile açılır; yanlışlıkla yazılamaz.
- Codex1'in `file_path / graph_path / meta_path / labels_path` alanları
  görece olabilir; `resolve_artifact` dataset köküne göre çözer.
- ifcopenshell'in geometry kernel'i (OpenCascade) yoksa 3D sekmesi açıklayıcı
  hata verir, ama browser/graph/etiket çalışmaya devam eder.
