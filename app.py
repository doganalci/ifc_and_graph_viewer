"""Erişilebilirlik Dataset Viewer — codex1 violation_pool dataset'i için
read-only Streamlit inceleyici."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from viewer import db
from viewer.config import DatasetPaths, default_root, resolve_artifact

st.set_page_config(
    page_title="Erişilebilirlik Dataset Viewer",
    page_icon="🔎",
    layout="wide",
)


def _paths() -> DatasetPaths | None:
    root = st.session_state.get("dataset_root") or default_root()
    p = DatasetPaths.from_root(root)
    return p if p.is_valid else None


def _sidebar() -> DatasetPaths | None:
    st.sidebar.markdown("### 📂 Dataset")
    current = st.session_state.get("dataset_root", default_root())
    new = st.sidebar.text_input(
        "Kök yol (codex1)",
        value=current,
        help="violation_pool.sqlite ve ifc_models/ klasörünün bulunduğu yol",
    )
    if new != current:
        st.session_state["dataset_root"] = new
        st.cache_data.clear()

    paths = DatasetPaths.from_root(new)
    if not paths.is_valid:
        st.sidebar.error(f"❌ Bulunamadı: {paths.db}")
        return None

    st.sidebar.success(f"✅ {paths.root}")
    s = _summary(paths.db)
    c1, c2 = st.sidebar.columns(2)
    c1.metric("Havuz (run)", s["runs"])
    c2.metric("İhlal kuralı", s["violations"])
    c1.metric("Baseline IFC", s["baseline"])
    c2.metric("Violated IFC", s["violated"])
    c1.metric("Imported", s["imported"])
    c2.metric("Etiket", s["labels"])
    c1.metric("Decoy", s["decoys"])
    c2.metric("LLM çağrı", s["llm_calls"])
    st.sidebar.metric("Toplam token", f"{s['tokens']:,}")
    return paths


@st.cache_data(show_spinner=False)
def _summary(db_path_str: str) -> dict:
    return db.db_summary(Path(db_path_str))


@st.cache_data(show_spinner=False)
def _ifc_models(db_path_str: str) -> list[dict]:
    return db.list_ifc_models(Path(db_path_str))


@st.cache_data(show_spinner=False)
def _label_counts(db_path_str: str) -> dict[str, dict[str, int]]:
    return db.count_labels_per_ifc(Path(db_path_str))


@st.cache_data(show_spinner=False)
def _runs(db_path_str: str) -> list[dict]:
    return db.list_runs(Path(db_path_str))


def _ifc_dataframe(paths: DatasetPaths) -> pd.DataFrame:
    models = _ifc_models(str(paths.db))
    counts = _label_counts(str(paths.db))
    runs = {r["id"]: r for r in _runs(str(paths.db))}
    rows = []
    for m in models:
        c = counts.get(m["id"], {})
        pool = runs.get(m.get("pool_run_id"))
        rows.append({
            "id": m["id"],
            "kind": m["kind"],
            "name": m["name"],
            "status": m["status"],
            "labels": c.get("total", 0),
            "applied": c.get("applied", 0),
            "decoy": c.get("decoy", 0),
            "skipped": c.get("skipped", 0),
            "parent_id": m.get("parent_id") or "",
            "pool_run": pool["name"] if pool else "",
            "pool_run_id": m.get("pool_run_id") or "",
            "llm_model": m["llm_model"],
            "error": m.get("error") or "",
            "created_at": m["created_at"],
        })
    return pd.DataFrame(rows)


# ---------------- Browser ----------------
def page_browser(paths: DatasetPaths) -> None:
    df = _ifc_dataframe(paths)
    if df.empty:
        st.info("Henüz hiç IFC üretilmemiş.")
        return

    st.subheader("🗂️ IFC Modelleri")
    f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
    with f1:
        kinds = ["(hepsi)"] + sorted(df["kind"].unique().tolist())
        kind_sel = st.selectbox("Tür", kinds, index=0)
    with f2:
        statuses = ["(hepsi)"] + sorted(df["status"].unique().tolist())
        status_sel = st.selectbox("Status", statuses, index=0)
    with f3:
        runs_list = ["(hepsi)"] + sorted({p for p in df["pool_run"].tolist() if p})
        pool_sel = st.selectbox("Havuz", runs_list, index=0)
    with f4:
        q = st.text_input("Ara (name / id)", "")

    fdf = df.copy()
    if kind_sel != "(hepsi)":
        fdf = fdf[fdf["kind"] == kind_sel]
    if status_sel != "(hepsi)":
        fdf = fdf[fdf["status"] == status_sel]
    if pool_sel != "(hepsi)":
        fdf = fdf[fdf["pool_run"] == pool_sel]
    if q:
        ql = q.lower()
        fdf = fdf[
            fdf["name"].str.lower().str.contains(ql, na=False)
            | fdf["id"].str.lower().str.contains(ql, na=False)
        ]

    min_labels = st.slider(
        "En az etiket sayısı",
        0,
        int(max(fdf["labels"].max() if not fdf.empty else 0, 1)),
        0,
    )
    if min_labels > 0:
        fdf = fdf[fdf["labels"] >= min_labels]

    st.caption(f"{len(fdf)} kayıt")
    st.dataframe(
        fdf,
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "id": st.column_config.TextColumn("id", width="medium"),
            "parent_id": st.column_config.TextColumn("parent", width="small"),
            "pool_run_id": st.column_config.TextColumn("pool_run_id", width="small"),
            "error": st.column_config.TextColumn("error", width="small"),
        },
    )

    st.markdown("---")
    st.markdown("### 🔍 Detay aç")
    if fdf.empty:
        return
    options = {
        f"[{r.kind}] {r.name}  ·  {r.id[:8]}  ·  {r.labels} etiket": r.id
        for r in fdf.itertuples()
    }
    sel_label = st.selectbox("Bir IFC seç", list(options.keys()))
    if st.button("Detayı aç →", type="primary"):
        st.session_state["detail_ifc_id"] = options[sel_label]
        st.session_state["active_tab"] = "Detay"
        st.rerun()


# ---------------- Detail ----------------
def page_detail(paths: DatasetPaths) -> None:
    ifc_id = st.session_state.get("detail_ifc_id")
    if not ifc_id:
        st.info("Önce **Browser**'dan bir IFC seç.")
        return

    model = db.get_ifc_model(paths.db, ifc_id)
    if not model:
        st.error(f"IFC bulunamadı: {ifc_id}")
        return

    labels = db.list_ifc_labels(paths.db, ifc_id)
    hl = {l["ifc_global_id"] for l in labels
          if l.get("ifc_global_id") and not l.get("is_decoy")}
    dc = {l["ifc_global_id"] for l in labels
          if l.get("ifc_global_id") and l.get("is_decoy")}

    h1, h2 = st.columns([3, 1])
    h1.subheader(f"{model['kind'].upper()} — {model['name']}")
    h1.caption(f"id: `{model['id']}`  ·  status: `{model['status']}`  ·  "
               f"oluşturma: {model['created_at']}")
    h2.metric("Etiket", len(labels))

    info_cols = st.columns(4)
    info_cols[0].metric("Applied", sum(1 for l in labels
                                       if l["status"] == "applied" and not l["is_decoy"]))
    info_cols[1].metric("Decoy", sum(1 for l in labels if l["is_decoy"]))
    info_cols[2].metric("Skipped", sum(1 for l in labels if l["status"] == "skipped"))
    usage = db.usage_totals(paths.db, ifc_model_id=ifc_id)
    info_cols[3].metric("Token (bu IFC)", f"{usage['total_tokens']:,}")

    t_3d, t_graph, t_labels, t_meta, t_files = st.tabs(
        ["🧱 3D", "🕸️ Graph", "🏷️ Etiketler", "📄 Meta", "📥 Dosyalar"]
    )

    with t_3d:
        ifc_path = resolve_artifact(paths, model.get("file_path"))
        if not ifc_path:
            st.error(f"IFC dosyası bulunamadı: {model.get('file_path')}")
        else:
            with st.spinner("Geometri tessellate ediliyor..."):
                try:
                    from viewer.ifc3d import ifc_to_figure
                    fig, info = ifc_to_figure(ifc_path, hl, dc)
                    st.plotly_chart(fig, use_container_width=True,
                                    config={"scrollZoom": True})
                    st.caption(f"Çizilen eleman: {info['drawn']}  ·  "
                               f"Atlanan: {info['skipped']}  ·  "
                               f"İhlal GUID: {len(hl)}  ·  Decoy GUID: {len(dc)}")
                except Exception as e:
                    st.error(f"3D çizim başarısız: {e}")

    with t_graph:
        graph_path = resolve_artifact(paths, model.get("graph_path"))
        if not graph_path:
            st.warning("Graph JSON yok. (codex1 daha eski sürümle üretildiyse "
                       "`graph_path` boş olabilir.)")
        else:
            try:
                from viewer.graph_view import load_graph, graph_to_figure
                g = load_graph(graph_path)
                fig = graph_to_figure(g, hl, dc)
                st.plotly_chart(fig, use_container_width=True,
                                config={"scrollZoom": True})
                st.caption(f"Nodes: {g.number_of_nodes()}  ·  "
                           f"Edges: {g.number_of_edges()}")
            except Exception as e:
                st.error(f"Graph çizim başarısız: {e}")

    with t_labels:
        if not labels:
            st.info("Bu IFC'de etiket yok.")
        else:
            ldf = pd.DataFrame([
                {
                    "title": l["title"],
                    "category": l["category"],
                    "severity": l["severity"],
                    "status": l["status"],
                    "decoy": "✓" if l["is_decoy"] else "",
                    "action": l["action"],
                    "ifc_type": l["ifc_type"],
                    "attribute": l["attribute"],
                    "before": l["value_before"],
                    "after": l["value_after"],
                    "guid": l["ifc_global_id"],
                    "reason": l["reason"],
                }
                for l in labels
            ])
            st.dataframe(ldf, use_container_width=True, hide_index=True, height=380)

            with st.expander("🔗 Kanıt zinciri — etiket detayı"):
                idx = st.number_input("Satır (0-bazlı)", 0,
                                      max(len(labels) - 1, 0), 0, key="lbl_idx")
                lab = labels[int(idx)]
                st.json({
                    "title": lab["title"],
                    "category": lab["category"],
                    "severity": lab["severity"],
                    "threshold": lab["threshold"],
                    "status": lab["status"],
                    "is_decoy": bool(lab["is_decoy"]),
                    "action": lab["action"],
                    "ifc_type": lab["ifc_type"],
                    "ifc_global_id": lab["ifc_global_id"],
                    "attribute": lab["attribute"],
                    "value_before": lab["value_before"],
                    "value_after": lab["value_after"],
                    "reason": lab["reason"],
                })
                try:
                    ev = json.loads(lab.get("evidence_json") or "[]")
                    if ev:
                        st.markdown("**Kanıtlar:**")
                        st.dataframe(pd.DataFrame(ev),
                                     use_container_width=True, hide_index=True)
                except Exception:
                    pass
                vid = lab.get("violation_id")
                if vid:
                    pool = db.get_violation(paths.db, vid)
                    if pool:
                        st.markdown("**Havuz kaydı:**")
                        st.json({k: v for k, v in pool.items()
                                 if k not in ("evidence",)})

    with t_meta:
        meta_path = resolve_artifact(paths, model.get("meta_path"))
        if meta_path:
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                st.json(meta)
            except Exception as e:
                st.error(f"meta.json okunamadı: {e}")
        else:
            st.info("meta.json yok.")
        try:
            params = json.loads(model.get("params_json") or "{}")
            if params:
                st.markdown("**params_json (DB)**")
                st.json(params)
        except Exception:
            pass
        if model.get("prompt"):
            with st.expander("Prompt"):
                st.code(model["prompt"])

    with t_files:
        for key, label in [("file_path", "IFC"),
                           ("meta_path", "meta.json"),
                           ("labels_path", "labels.json"),
                           ("graph_path", "graph.json")]:
            p = resolve_artifact(paths, model.get(key))
            if p:
                try:
                    data = p.read_bytes()
                    st.download_button(
                        f"⬇️ {label} ({p.name}, {len(data) / 1024:.1f} KB)",
                        data=data,
                        file_name=p.name,
                        key=f"dl_{key}",
                    )
                except Exception as e:
                    st.warning(f"{label}: {e}")
            else:
                st.caption(f"— {label}: yok")


# ---------------- Main ----------------
def main() -> None:
    paths = _sidebar()
    st.title("🔎 Erişilebilirlik Dataset Viewer")
    st.caption("TS 9111 / TS ISO 21542 ihlal havuzu ve ihlalli IFC dataset'i — read-only inceleme.")

    if not paths:
        st.error(
            "Geçerli bir dataset köküne ihtiyaç var. Sol panelden codex1 "
            "kök yolunu (içinde `violation_pool.sqlite` olan klasör) ver."
        )
        return

    tab_browser, tab_detail = st.tabs(["🗂️ Browser", "🔍 Detay"])
    with tab_browser:
        page_browser(paths)
    with tab_detail:
        page_detail(paths)


if __name__ == "__main__":
    main()
