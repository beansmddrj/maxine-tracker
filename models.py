from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final


APP_TITLE: Final[str] = "Maxine Mod Tracker"
APP_VERSION = "0.7.0"
DATA_FILE: Final[str] = "maxine_mods.json"
ASSETS_DIR: Final[str] = "maxine_assets"
AUTOSAVE_EVERY_MS: Final[int] = 20_000  # 20 seconds
SETTINGS_FILE: Final[str] = "maxine_settings.json"
DEFAULT_UI_SCALE: Final[float] = 1.45
DEFAULT_THEME: Final[str] = "dark"   # "dark" or "light"
DEFAULT_FONT_FAMILY: Final[str] = "Segoe UI"
DEFAULT_FONT_SIZE: Final[int] = 13



CATEGORIES: Final[list[str]] = [
    "Exhaust", "Engine", "Transmission", "Suspension", "Brakes", "Wheels/Tires",
    "Interior", "Exterior", "Electrical", "Maintenance", "Other"
]

STATUSES: Final[list[str]] = ["Planned", "In Progress", "Installed"]

SCOPES: Final[list[str]] = [
    "Full car",
    "Driver side",
    "Passenger side",
    "Front",
    "Rear",
    "Front driver",
    "Front passenger",
    "Rear driver",
    "Rear passenger",
    "Other / custom",
]

MAINT_TYPES: Final[list[str]] = [
    "Oil change",
    "Transmission fluid",
    "Coolant",
    "Brake fluid",
    "Power steering fluid",
    "Spark plugs",
    "Tires",
    "Brakes",
    "Alignment",
    "Battery",
    "Air filter",
    "Cabin filter",
    "Belts",
    "Other",
]


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def normalize_int(s: str) -> str:
    return s.replace(",", "").strip()


def normalize_money(s: str) -> str:
    return s.replace("$", "").replace(",", "").strip()


@dataclass
class VehicleInfo:
    id: str
    name: str
    year: int
    make: str
    model: str
