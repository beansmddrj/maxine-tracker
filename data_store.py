from __future__ import annotations
from models import DATA_FILE, ASSETS_DIR, SETTINGS_FILE, DEFAULT_UI_SCALE, DEFAULT_THEME, now_iso


import json
import os
import tempfile
from pathlib import Path
from typing import Any

from models import DATA_FILE, ASSETS_DIR, now_iso


def base_dir() -> Path:
    # Keep everything next to your scripts
    return Path(__file__).resolve().parent


def data_path() -> Path:
    return base_dir() / DATA_FILE


def assets_dir() -> Path:
    p = base_dir() / ASSETS_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(prefix="._mods_", suffix=".json", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


def default_data() -> dict[str, Any]:
    return {
        "schema": 1,
        "active_vehicle_id": "maxine-06-maxima",
        "vehicles": [{
            "id": "maxine-06-maxima",
            "name": "Maxine",
            "year": 2006,
            "make": "Nissan",
            "model": "Maxima",
            "current_mileage": None,
            "items": [],
            "maintenance": []
        }],
        "updated_at": now_iso()
    }


def load_data() -> dict[str, Any]:
    p = data_path()
    if not p.exists():
        return default_data()

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))

        # Backward compat: if file is a LIST, treat it as items list
        if isinstance(raw, list):
            d = default_data()
            d["vehicles"][0]["items"] = raw
            d["updated_at"] = now_iso()
            return d

        if isinstance(raw, dict) and raw.get("schema") == 1:
            raw.setdefault("updated_at", now_iso())
            raw.setdefault("active_vehicle_id", "maxine-06-maxima")
            raw.setdefault("vehicles", [])

            if not raw["vehicles"]:
                raw["vehicles"] = default_data()["vehicles"]

            for v in raw["vehicles"]:
                v.setdefault("current_mileage", None)
                v.setdefault("items", [])
                v.setdefault("maintenance", [])

            return raw
    except Exception:
        pass

    return default_data()


def save_data(data: dict[str, Any]) -> None:
    data["updated_at"] = now_iso()
    safe_write_json(data_path(), data)

def settings_path() -> Path:
    return base_dir() / SETTINGS_FILE


def default_settings() -> dict[str, Any]:
    return {
        "schema": 1,
        "theme": DEFAULT_THEME,          # "dark" or "light"
        "ui_scale": float(DEFAULT_UI_SCALE),
        "font_family": "Segoe UI",
        "font_size": 13,
        "autosave_ms": 20_000,
        "car_mode": False,
        "updated_at": now_iso(),
    }


def load_settings() -> dict[str, Any]:
    p = settings_path()
    if not p.exists():
        return default_settings()

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("schema") == 1:
            d = default_settings()
            # merge known keys only
            for k in d.keys():
                if k in raw:
                    d[k] = raw[k]
            d["updated_at"] = now_iso()
            # sanitize a bit
            if d["theme"] not in ("dark", "light"):
                d["theme"] = DEFAULT_THEME
            try:
                d["ui_scale"] = float(d["ui_scale"])
            except Exception:
                d["ui_scale"] = float(DEFAULT_UI_SCALE)
            try:
                d["autosave_ms"] = int(d["autosave_ms"])
            except Exception:
                d["autosave_ms"] = 20_000
            d["car_mode"] = bool(d.get("car_mode", False))
            return d
    except Exception:
        pass

    return default_settings()


def save_settings(settings: dict[str, Any]) -> None:
    settings["updated_at"] = now_iso()
    safe_write_json(settings_path(), settings)
