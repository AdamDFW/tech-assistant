

import streamlit as st
import os
import json
import time
import zipfile
from services.vin_service import normalize_vin, last6_from_vin
from services.validation.velogitech_rules import validate_velogitech
from datetime import datetime
from pathlib import Path
def ensure_work_order():
    if "work_order" not in st.session_state:
        st.session_state["work_order"] = {
            "project": "",
            "unit": "",
            "vin": "",
            "vin_last6": "",
            "photos": [],  # each: {"path":..., "type":"vin_plate", ...}
        }

ensure_work_order()
wo = st.session_state["work_order"]

APP_NAME = "Tech X2 v0.1"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


RECENT_PATH = DATA_DIR / "_recent.json"
RECENT_MAX = 10



def safe_name(s: str) -> str:
    s = (s or "").strip()
    keep = []
    for ch in s:
        if ch.isalnum() or ch in ("-", "_"):
            keep.append(ch)
        elif ch.isspace():
            keep.append("_")
    out = "".join(keep).strip("_")
    return out or "untitled"


def now_stamp() -> str:
    # sortable timestamp
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def unit_dir(project: str, unit: str) -> Path:
    return DATA_DIR / safe_name(project) / safe_name(unit)


def meta_path(project: str, unit: str) -> Path:
    return unit_dir(project, unit) / "meta.json"


def load_meta(project: str, unit: str) -> dict:
    p = meta_path(project, unit)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "project": project,
        "unit": unit,
        "created_at": datetime.now().isoformat(),
        "items": [],  # each: {filename, added_at, note}
    }


def save_meta(project: str, unit: str, meta: dict) -> None:
    d = unit_dir(project, unit)
    d.mkdir(parents=True, exist_ok=True)
    meta_path(project, unit).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def list_projects() -> list[str]:
    if not DATA_DIR.exists():
        return []
    return sorted([p.name for p in DATA_DIR.iterdir() if p.is_dir()])


def list_units(project: str) -> list[str]:
    pdir = DATA_DIR / safe_name(project)
    if not pdir.exists():
        return []
    return sorted([p.name for p in pdir.iterdir() if p.is_dir()])


def export_bundle(project: str, unit: str) -> Path:
    udir = unit_dir(project, unit)
    meta = load_meta(project, unit)

    exports = DATA_DIR / "_exports"
    exports.mkdir(parents=True, exist_ok=True)

    zip_name = f"{safe_name(project)}__{safe_name(unit)}__{now_stamp()}.zip"
    zip_path = exports / zip_name

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # include meta
        z.writestr("meta.json", json.dumps(meta, indent=2))
        # include images
        for item in meta.get("items", []):
            f = udir / item["filename"]
            if f.exists():
                z.write(f, arcname=f"photos/{f.name}")

    return zip_path

# =========================
# Recent Units Feature (v0.2)
# =========================


RECENT_MAX = 10  # keep a little history, we’ll display last 3


def load_recent() -> list[dict]:
    if RECENT_PATH.exists():
        try:
            return json.loads(RECENT_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_recent(items: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    RECENT_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


def bump_recent(project: str, unit: str) -> None:
    project_s = safe_name(project)
    unit_s = safe_name(unit)

    items = load_recent()
    # remove existing match
    items = [x for x in items if not (x.get("project") == project_s and x.get("unit") == unit_s)]
    # add to front
    items.insert(0, {"project": project_s, "unit": unit_s, "touched_at": datetime.now().isoformat()})
    # trim
    items = items[:RECENT_MAX]
    save_recent(items)

def count_photos(project: str, unit: str) -> int:
    photos_path = unit_dir(project, unit) / "photos"
    if photos_path.exists():
        return len(list(photos_path.glob("*.*")))
    return 0


st.set_page_config(page_title=APP_NAME, layout="wide")
st.title(APP_NAME)
DATA_DIR.mkdir(exist_ok=True)

# Sidebar: choose project/unit
st.sidebar.header("Context")

projects = list_projects()
project = st.sidebar.text_input("Project", value=projects[0] if projects else "Irdeto")
units = list_units(project)
unit = st.sidebar.text_input("Unit # / VIN", value=units[-1] if units else "")

colA, colB = st.sidebar.columns(2)
with colA:
    if st.button("Create / Open Unit", use_container_width=True):
        if unit.strip():
            md = load_meta(project, unit)
            save_meta(project, unit, md)

        # update recent units list
        bump_recent(project, unit)

        st.session_state["active_project"] = project
        st.session_state["active_unit"] = unit

with colB:
    if st.button("Clear", use_container_width=True):
        st.session_state.pop("active_project", None)
        st.session_state.pop("active_unit", None)

active_project = st.session_state.get("active_project")
active_unit = st.session_state.get("active_unit")


if not active_project or not active_unit:
    st.markdown("### Quick Start")

    recent = load_recent()
    
         
    if recent:
        st.markdown("#### Recent Units")
        top3 = recent[:3]
        cols = st.columns(len(top3))
        for col, item in zip(cols, top3):
            with col:
                p = item["project"]
                u = item["unit"]



                photo_count = count_photos(p, u)
                updated = item.get("touched_at", "")[:16].replace("T", " ")

                st.markdown(f"""
                <div style="padding:10px; border:1px solid #444; border-radius:8px;">
                <b>{p} → {u}</b><br>
                <small>🕒 {updated}</small><br>
                <small>📸 {photo_count} photos</small>
                </div>
                """, unsafe_allow_html=True)


                if st.button("Open", key=f"open_{p}_{u}", use_container_width=True):
                    md = load_meta(p, u)
                    save_meta(p, u, md)
                    bump_recent(p, u)
                    st.session_state["active_project"] = p
                    st.session_state["active_unit"] = u
                    st.rerun()

else:
    st.caption("No recent units yet. Create/Open a unit to start building your list.")
    st.info("Enter a Project and Unit #/VIN on the left, then click **Create / Open Unit**.")
    st.stop()


st.subheader(f"Active: {active_project} → {active_unit}")

udir = unit_dir(active_project, active_unit)
udir.mkdir(parents=True, exist_ok=True)

meta = load_meta(active_project, active_unit)
# Capture section

tab_home, tab_capture, tab_timeline, tab_export = st.tabs(
    ["🏠 Home", "📸 Capture", "🧾 Timeline", "📦 Export"]
)

with tab_capture:
    st.markdown("## 📸 Capture Photo")

    uploads = st.file_uploader(
        "Tap to capture or select photo",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
    )



note = st.text_input("Optional note for this batch (e.g., 'VIN plate', 'curb side front hub')")

if uploads:
    added = 0
    for up in uploads:
        ext = Path(up.name).suffix.lower() or ".jpg"
        fname = f"{now_stamp()}__{safe_name(Path(up.name).stem)}{ext}"
        outpath = udir / fname
        outpath.write_bytes(up.getbuffer())
        meta["items"].append(
            {
                "filename": fname,
                "added_at": datetime.now().isoformat(),
                "note": note.strip(),
            }
        )
        added += 1
        time.sleep(0.01)  # ensures timestamp uniqueness in fast loops
    save_meta(active_project, active_unit, meta)
    st.success(f"Added {added} photo(s).")
    st.rerun()

# Timeline view
st.markdown("### Capture timeline (in order)")
items = meta.get("items", [])

if not items:
    st.warning("No photos yet.")
else:
    # newest last (already appended that way)
    for i, item in enumerate(items, start=1):
        f = udir / item["filename"]
        cols = st.columns([1, 2])
        with cols[0]:
            if f.exists():
                st.image(str(f), use_container_width=True)
        with cols[1]:
            st.write(f"**#{i}** — `{item['filename']}`")
            st.write(f"Added: {item.get('added_at','')}")
            n = item.get("note", "").strip()
            st.write(f"Note: {n if n else '—'}")

st.divider()

# Export
st.markdown("### Export backup bundle")
col1, col2 = st.columns([1, 2])
with col1:
    if st.button("Export ZIP bundle", use_container_width=True):
        zp = export_bundle(active_project, active_unit)
        st.session_state["last_export"] = str(zp)
        st.success("Export created.")
with col2:
    last = st.session_state.get("last_export")
    if last:
        st.code(last)
        with open(last, "rb") as f:
            st.download_button(
                "Download latest export",
                data=f,
                file_name=Path(last).name,
                mime="application/zip",
                use_container_width=True,
            )
