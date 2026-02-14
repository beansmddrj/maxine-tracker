import json
import os
import sys
import shutil
import tempfile
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


APP_TITLE = "Maxine Mod Tracker"
DATA_FILE = "maxine_mods.json"
ASSETS_DIR = "maxine_assets"
AUTOSAVE_EVERY_MS = 20_000  # 20s


# -------------------------
# Helpers
# -------------------------
def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def normalize_int(s: str) -> str:
    return s.replace(",", "").strip()


def normalize_money(s: str) -> str:
    return s.replace("$", "").replace(",", "").strip()


def safe_write_json(path: str, data: dict) -> None:
    folder = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="._mods_", suffix=".json", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def ensure_assets_dir() -> str:
    base = os.path.dirname(os.path.abspath(DATA_FILE)) or "."
    folder = os.path.join(base, ASSETS_DIR)
    os.makedirs(folder, exist_ok=True)
    return folder


def unique_dest_path(dest_folder: str, src_path: str) -> str:
    base = os.path.basename(src_path)
    name, ext = os.path.splitext(base)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = os.path.join(dest_folder, f"{name}_{stamp}{ext}")
    i = 1
    while os.path.exists(candidate):
        candidate = os.path.join(dest_folder, f"{name}_{stamp}_{i}{ext}")
        i += 1
    return candidate


def open_file_with_default_app(path: str) -> None:
    if not path or not os.path.exists(path):
        raise FileNotFoundError("File not found.")
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


# -------------------------
# Data
# -------------------------
def load_data() -> dict:
    """
    Schema 1:
    {
      "schema": 1,
      "active_vehicle_id": "...",
      "vehicles": [
        {
          "id": "...",
          "name": "Maxine",
          "year": 2006,
          "make": "Nissan",
          "model": "Maxima",
          "current_mileage": 150000,
          "items": [ ... mods/repairs ... ],
          "maintenance": [ ... maintenance tasks ... ]
        }
      ],
      "updated_at": "..."
    }

    Backward compat:
    - If file is LIST -> becomes vehicles[0].items
    """
    if not os.path.exists(DATA_FILE):
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

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, list):
            # old list format
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
                    "items": raw,
                    "maintenance": []
                }],
                "updated_at": now_iso()
            }

        if isinstance(raw, dict) and raw.get("schema") == 1:
            if "vehicles" not in raw or not isinstance(raw["vehicles"], list) or not raw["vehicles"]:
                raw["vehicles"] = [{
                    "id": "maxine-06-maxima",
                    "name": "Maxine",
                    "year": 2006,
                    "make": "Nissan",
                    "model": "Maxima",
                    "current_mileage": None,
                    "items": [],
                    "maintenance": []
                }]
            if "active_vehicle_id" not in raw:
                raw["active_vehicle_id"] = raw["vehicles"][0].get("id", "maxine-06-maxima")
            if "updated_at" not in raw:
                raw["updated_at"] = now_iso()

            # ensure per-vehicle keys exist
            for v in raw["vehicles"]:
                v.setdefault("current_mileage", None)
                v.setdefault("items", [])
                v.setdefault("maintenance", [])
            return raw
    except Exception:
        pass

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


# -------------------------
# Full-page Mod/Repair editor
# -------------------------
CATEGORIES = ["Exhaust", "Engine", "Transmission", "Suspension", "Brakes", "Wheels/Tires",
              "Interior", "Exterior", "Electrical", "Maintenance", "Other"]

STATUSES = ["Planned", "In Progress", "Installed"]

SCOPES = [
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


class ItemEditor(tk.Toplevel):
    def __init__(self, parent, item: dict, on_save):
        super().__init__(parent)
        self.title("Edit mod / repair")
        self.minsize(860, 600)
        self.on_save = on_save
        self._item = dict(item)

        self.var_name = tk.StringVar(value=self._item.get("name", ""))
        self.var_category = tk.StringVar(value=self._item.get("category", "Exhaust"))
        self.var_status = tk.StringVar(value=self._item.get("status", "Installed"))
        self.var_scope = tk.StringVar(value=self._item.get("scope", "Full car"))
        self.var_date = tk.StringVar(value=self._item.get("date", today_str()))
        self.var_mileage = tk.StringVar(value=str(self._item.get("mileage", "")))
        self.var_cost = tk.StringVar(value=str(self._item.get("cost", "")))
        self.var_copy_assets = tk.BooleanVar(value=True)

        self.attachments = list(self._item.get("attachments", []))
        if not isinstance(self.attachments, list):
            self.attachments = []

        self._build_ui()

        notes_text = self._item.get("notes", "")
        self.txt_notes.insert("1.0", notes_text if isinstance(notes_text, str) else "")
        self._load_attachments()

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Control-s>", lambda _e: self._save())

        self.update_idletasks()
        x = parent.winfo_rootx() + 40
        y = parent.winfo_rooty() + 40
        self.geometry(f"+{x}+{y}")

        self.grab_set()
        self.focus_set()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Mod / Repair Editor", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Ctrl+S saves", foreground="#666").grid(row=0, column=1, sticky="e")

        nb = ttk.Notebook(outer)
        nb.grid(row=1, column=0, sticky="nsew")

        tab_details = ttk.Frame(nb, padding=12)
        tab_notes = ttk.Frame(nb, padding=12)
        tab_files = ttk.Frame(nb, padding=12)

        nb.add(tab_details, text="Details")
        nb.add(tab_notes, text="Notes")
        nb.add(tab_files, text="Photos & Receipts")

        # Details
        tab_details.columnconfigure(1, weight=1)
        r = 0
        ttk.Label(tab_details, text="Name *").grid(row=r, column=0, sticky="w")
        ttk.Entry(tab_details, textvariable=self.var_name).grid(row=r, column=1, sticky="ew", pady=6)
        r += 1

        ttk.Label(tab_details, text="Category").grid(row=r, column=0, sticky="w")
        ttk.Combobox(tab_details, textvariable=self.var_category, values=CATEGORIES, state="readonly")\
            .grid(row=r, column=1, sticky="ew", pady=6)
        r += 1

        ttk.Label(tab_details, text="Status").grid(row=r, column=0, sticky="w")
        ttk.Combobox(tab_details, textvariable=self.var_status, values=STATUSES, state="readonly")\
            .grid(row=r, column=1, sticky="ew", pady=6)
        r += 1

        ttk.Label(tab_details, text="Scope (side/area)").grid(row=r, column=0, sticky="w")
        ttk.Combobox(tab_details, textvariable=self.var_scope, values=SCOPES, state="readonly")\
            .grid(row=r, column=1, sticky="ew", pady=6)
        r += 1

        ttk.Label(tab_details, text="Date (YYYY-MM-DD)").grid(row=r, column=0, sticky="w")
        ttk.Entry(tab_details, textvariable=self.var_date).grid(row=r, column=1, sticky="ew", pady=6)
        r += 1

        ttk.Label(tab_details, text="Mileage").grid(row=r, column=0, sticky="w")
        ttk.Entry(tab_details, textvariable=self.var_mileage).grid(row=r, column=1, sticky="ew", pady=6)
        r += 1

        ttk.Label(tab_details, text="Cost ($)").grid(row=r, column=0, sticky="w")
        ttk.Entry(tab_details, textvariable=self.var_cost).grid(row=r, column=1, sticky="ew", pady=6)
        r += 1

        ttk.Separator(tab_details).grid(row=r, column=0, columnspan=2, sticky="ew", pady=12)
        r += 1

        ttk.Checkbutton(
            tab_details,
            text=f"Copy uploaded files into {ASSETS_DIR} (recommended)",
            variable=self.var_copy_assets
        ).grid(row=r, column=0, columnspan=2, sticky="w")

        # Notes (big)
        tab_notes.rowconfigure(0, weight=1)
        tab_notes.columnconfigure(0, weight=1)
        notes_frame = ttk.Frame(tab_notes)
        notes_frame.grid(row=0, column=0, sticky="nsew")
        notes_frame.rowconfigure(0, weight=1)
        notes_frame.columnconfigure(0, weight=1)

        self.txt_notes = tk.Text(notes_frame, wrap="word")
        self.txt_notes.grid(row=0, column=0, sticky="nsew")
        notes_scroll = ttk.Scrollbar(notes_frame, orient="vertical", command=self.txt_notes.yview)
        self.txt_notes.configure(yscrollcommand=notes_scroll.set)
        notes_scroll.grid(row=0, column=1, sticky="ns")

        # Files
        tab_files.rowconfigure(1, weight=1)
        tab_files.columnconfigure(0, weight=1)

        ttk.Label(tab_files, text="Double-click to open").grid(row=0, column=0, sticky="w")

        file_area = ttk.Frame(tab_files)
        file_area.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        file_area.rowconfigure(0, weight=1)
        file_area.columnconfigure(0, weight=1)

        self.lst_files = tk.Listbox(file_area)
        self.lst_files.grid(row=0, column=0, sticky="nsew")
        fscroll = ttk.Scrollbar(file_area, orient="vertical", command=self.lst_files.yview)
        self.lst_files.configure(yscrollcommand=fscroll.set)
        fscroll.grid(row=0, column=1, sticky="ns")
        self.lst_files.bind("<Double-1>", lambda _e: self._open_selected())

        btn_row = ttk.Frame(tab_files)
        btn_row.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for i in range(5):
            btn_row.columnconfigure(i, weight=1)

        ttk.Button(btn_row, text="Add Photo(s)", command=lambda: self._add_files("Photo")).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(btn_row, text="Add Receipt(s)", command=lambda: self._add_files("Receipt")).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(btn_row, text="Add File(s)", command=lambda: self._add_files("File")).grid(row=0, column=2, sticky="ew", padx=6)
        ttk.Button(btn_row, text="Open", command=self._open_selected).grid(row=0, column=3, sticky="ew", padx=6)
        ttk.Button(btn_row, text="Remove", command=self._remove_selected).grid(row=0, column=4, sticky="ew", padx=(6, 0))

        # Bottom controls
        bottom = ttk.Frame(outer)
        bottom.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        bottom.columnconfigure(0, weight=1)
        ttk.Button(bottom, text="Save changes", command=self._save).grid(row=0, column=1, sticky="e", padx=(0, 8))
        ttk.Button(bottom, text="Cancel", command=self.destroy).grid(row=0, column=2, sticky="e")

    def _load_attachments(self):
        self.lst_files.delete(0, tk.END)
        for a in self.attachments:
            kind = a.get("kind", "File")
            label = a.get("label") or os.path.basename(a.get("path", "")) or "(missing)"
            self.lst_files.insert(tk.END, f"[{kind}] {label}")

    def _add_files(self, kind: str):
        paths = filedialog.askopenfilenames(title=f"Select {kind}(s)", filetypes=[("All files", "*.*")])
        if not paths:
            return

        copy_into_assets = bool(self.var_copy_assets.get())
        assets_folder = ensure_assets_dir() if copy_into_assets else None

        for p in paths:
            p = str(p)
            final_path = p
            if copy_into_assets:
                try:
                    dest = unique_dest_path(assets_folder, p)
                    shutil.copy2(p, dest)
                    final_path = dest
                except Exception as e:
                    messagebox.showwarning("Copy failed", f"Could not copy:\n{p}\n\nReason: {e}\n\nLinking original instead.")
                    final_path = p

            self.attachments.append({
                "kind": kind,
                "path": final_path,
                "label": os.path.basename(final_path),
                "added_at": now_iso(),
            })

        self._load_attachments()

    def _sel_index(self):
        sel = self.lst_files.curselection()
        return int(sel[0]) if sel else None

    def _open_selected(self):
        idx = self._sel_index()
        if idx is None:
            messagebox.showinfo("Nothing selected", "Select an attachment first.", parent=self)
            return
        att = self.attachments[idx]
        path = att.get("path", "")
        try:
            open_file_with_default_app(path)
        except Exception as e:
            messagebox.showerror("Open failed", f"Could not open:\n{path}\n\n{e}", parent=self)

    def _remove_selected(self):
        idx = self._sel_index()
        if idx is None:
            messagebox.showinfo("Nothing selected", "Select an attachment first.", parent=self)
            return
        att = self.attachments[idx]
        label = att.get("label", "this file")
        if not messagebox.askyesno("Remove", f"Remove attachment:\n{label}\n\n(Not deleting the file from disk.)", parent=self):
            return
        self.attachments.pop(idx)
        self._load_attachments()

    def _save(self):
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Missing info", "Name is required.", parent=self)
            return

        mileage = self.var_mileage.get().strip()
        cost = self.var_cost.get().strip()

        if mileage:
            try:
                int(normalize_int(mileage))
            except ValueError:
                messagebox.showerror("Invalid mileage", "Mileage should be a whole number (ex: 150000).", parent=self)
                return

        if cost:
            try:
                float(normalize_money(cost))
            except ValueError:
                messagebox.showerror("Invalid cost", "Cost should be a number (ex: 199.99).", parent=self)
                return

        notes = self.txt_notes.get("1.0", "end").rstrip()

        updated = {
            "date": self.var_date.get().strip() or today_str(),
            "name": name,
            "category": self.var_category.get(),
            "status": self.var_status.get(),
            "scope": self.var_scope.get(),
            "mileage": mileage,
            "cost": cost,
            "notes": notes,
            "attachments": self.attachments,
            "updated_at": now_iso(),
        }
        self.on_save(updated)
        self.destroy()


# -------------------------
# Maintenance basics (simple)
# -------------------------
MAINT_TYPES = ["Oil change", "Transmission fluid", "Coolant", "Brake fluid", "Power steering fluid",
               "Spark plugs", "Tires", "Brakes", "Alignment", "Battery", "Air filter", "Cabin filter",
               "Belts", "Other"]


class ModTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.data = load_data()
        self.active_vehicle = self._get_active_vehicle()

        self.title(f"{APP_TITLE} — {self.active_vehicle.get('name','Vehicle')}")
        self.minsize(1150, 680)

        self.last_saved_at = None
        self.dirty = False
        self.sort_state = {"col": None, "desc": False}

        self._build_ui()
        self._refresh_all()

        self.after(AUTOSAVE_EVERY_MS, self._autosave_tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _get_active_vehicle(self) -> dict:
        vid = self.data.get("active_vehicle_id")
        for v in self.data.get("vehicles", []):
            if v.get("id") == vid:
                return v
        return self.data["vehicles"][0]

    @property
    def items(self) -> list[dict]:
        return self.active_vehicle.setdefault("items", [])

    @property
    def maintenance(self) -> list[dict]:
        return self.active_vehicle.setdefault("maintenance", [])

    def _mark_dirty(self):
        self.dirty = True
        self._update_status()

    def _save(self, force=False):
        if not self.dirty and not force:
            return
        self.data["updated_at"] = now_iso()
        safe_write_json(DATA_FILE, self.data)
        self.last_saved_at = now_iso()
        self.dirty = False
        self._update_status()

    def _autosave_tick(self):
        self._save(force=False)
        self.after(AUTOSAVE_EVERY_MS, self._autosave_tick)

    def _on_close(self):
        self._save(force=True)
        self.destroy()

    # ---------------- UI ----------------
    def _build_ui(self):
        top = ttk.Frame(self, padding=(12, 12, 12, 6))
        top.pack(fill="x")

        ttk.Label(top, text=f"{APP_TITLE} — {self.active_vehicle.get('name','')}",
                  font=("Segoe UI", 16, "bold")).pack(side="left")

        # Current mileage control (helps maintenance later)
        right = ttk.Frame(top)
        right.pack(side="right")

        ttk.Label(right, text="Current mileage").pack(side="left", padx=(0, 6))
        self.var_current_mileage = tk.StringVar(
            value="" if self.active_vehicle.get("current_mileage") is None else str(self.active_vehicle.get("current_mileage"))
        )
        cm_entry = ttk.Entry(right, textvariable=self.var_current_mileage, width=10)
        cm_entry.pack(side="left")
        ttk.Button(right, text="Set", command=self.set_current_mileage).pack(side="left", padx=(6, 0))

        # Main notebook (Mods/Repairs + Maintenance)
        self.main_nb = ttk.Notebook(self)
        self.main_nb.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_mods = ttk.Frame(self.main_nb)
        self.tab_maint = ttk.Frame(self.main_nb)

        self.main_nb.add(self.tab_mods, text="Mods & Repairs")
        self.main_nb.add(self.tab_maint, text="Maintenance")

        self._build_mods_tab()
        self._build_maintenance_tab()

        # Status bar
        self.status = ttk.Label(self, text="", anchor="w")
        self.status.pack(fill="x", padx=12, pady=(0, 10))
        self._update_status()

    def _build_mods_tab(self):
        self.tab_mods.columnconfigure(0, weight=1)
        self.tab_mods.columnconfigure(1, weight=2)
        self.tab_mods.rowconfigure(0, weight=1)

        # Left: quick add
        form = ttk.LabelFrame(self.tab_mods, text="Quick add (mods/repairs)", padding=12)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        form.columnconfigure(1, weight=1)
        form.rowconfigure(8, weight=1)

        self.var_name = tk.StringVar()
        self.var_category = tk.StringVar(value="Suspension")
        self.var_status = tk.StringVar(value="Planned")
        self.var_scope = tk.StringVar(value="Full car")
        self.var_date = tk.StringVar(value=today_str())
        self.var_mileage = tk.StringVar()
        self.var_cost = tk.StringVar()

        r = 0
        ttk.Label(form, text="Name *").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_name).grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(form, text="Category").grid(row=r, column=0, sticky="w")
        ttk.Combobox(form, textvariable=self.var_category, values=CATEGORIES, state="readonly")\
            .grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(form, text="Status").grid(row=r, column=0, sticky="w")
        ttk.Combobox(form, textvariable=self.var_status, values=STATUSES, state="readonly")\
            .grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(form, text="Scope (side/area)").grid(row=r, column=0, sticky="w")
        ttk.Combobox(form, textvariable=self.var_scope, values=SCOPES, state="readonly")\
            .grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(form, text="Date").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_date).grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(form, text="Mileage").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_mileage).grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(form, text="Cost ($)").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_cost).grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(form, text="Notes (quick)").grid(row=r, column=0, sticky="nw", pady=(6, 0))
        notes_frame = ttk.Frame(form)
        notes_frame.grid(row=r, column=1, sticky="nsew", pady=(6, 0))
        notes_frame.rowconfigure(0, weight=1)
        notes_frame.columnconfigure(0, weight=1)

        self.txt_quick_notes = tk.Text(notes_frame, wrap="word", height=8)
        self.txt_quick_notes.grid(row=0, column=0, sticky="nsew")
        qscroll = ttk.Scrollbar(notes_frame, orient="vertical", command=self.txt_quick_notes.yview)
        self.txt_quick_notes.configure(yscrollcommand=qscroll.set)
        qscroll.grid(row=0, column=1, sticky="ns")
        r += 1

        btns = ttk.Frame(form)
        btns.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        ttk.Button(btns, text="Add", command=self.add_item).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(btns, text="Clear", command=self.clear_form).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Right: Search + notebook split (Pipeline vs Installed)
        right = ttk.LabelFrame(self.tab_mods, text="Log", padding=12)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        search_bar = ttk.Frame(right)
        search_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search_bar.columnconfigure(1, weight=1)

        ttk.Label(search_bar, text="Search").grid(row=0, column=0, sticky="w")
        self.var_search = tk.StringVar()
        ent = ttk.Entry(search_bar, textvariable=self.var_search)
        ent.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ent.bind("<KeyRelease>", lambda _e: self._refresh_mod_lists())

        self.mods_nb = ttk.Notebook(right)
        self.mods_nb.grid(row=1, column=0, sticky="ew")
        self.mods_nb.bind("<<NotebookTabChanged>>", lambda _e: self._sync_active_tree())

        self.tab_pipeline = ttk.Frame(self.mods_nb, padding=(0, 6, 0, 0))
        self.tab_installed = ttk.Frame(self.mods_nb, padding=(0, 6, 0, 0))
        self.mods_nb.add(self.tab_pipeline, text="Pipeline (Planned / In Progress)")
        self.mods_nb.add(self.tab_installed, text="Installed")

        # Pipeline tree
        self.tree_pipeline = self._make_mod_tree(self.tab_pipeline)
        # Installed tree
        self.tree_installed = self._make_mod_tree(self.tab_installed)

        # Actions (use whichever tab is active)
        actions = ttk.Frame(right)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        for i in range(4):
            actions.columnconfigure(i, weight=1)

        ttk.Button(actions, text="Open editor", command=self.edit_selected).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(actions, text="Delete selected", command=self.delete_selected).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(actions, text="Show totals", command=self.show_totals).grid(row=0, column=2, sticky="ew", padx=6)
        ttk.Button(actions, text="Save now", command=lambda: self._save(force=True)).grid(row=0, column=3, sticky="ew", padx=(6, 0))

        self.active_mod_tree = self.tree_pipeline

    def _make_mod_tree(self, parent) -> ttk.Treeview:
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        columns = ("date", "name", "category", "status", "scope", "mileage", "cost", "files", "notes")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=14)
        tree.grid(row=0, column=0, sticky="nsew")

        headings = {
            "date": "Date",
            "name": "Name",
            "category": "Category",
            "status": "Status",
            "scope": "Scope",
            "mileage": "Mileage",
            "cost": "Cost",
            "files": "Files",
            "notes": "Notes",
        }
        for col, text in headings.items():
            tree.heading(col, text=text)

        tree.column("date", width=92, anchor="w")
        tree.column("name", width=190, anchor="w")
        tree.column("category", width=110, anchor="w")
        tree.column("status", width=95, anchor="w")
        tree.column("scope", width=110, anchor="w")
        tree.column("mileage", width=84, anchor="e")
        tree.column("cost", width=72, anchor="e")
        tree.column("files", width=55, anchor="center")
        tree.column("notes", width=240, anchor="w")

        tree.bind("<Double-1>", lambda _e: self.edit_selected())

        scroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        return tree

    def _build_maintenance_tab(self):
        self.tab_maint.columnconfigure(0, weight=1)
        self.tab_maint.columnconfigure(1, weight=2)
        self.tab_maint.rowconfigure(0, weight=1)

        # Left: quick add maintenance task
        form = ttk.LabelFrame(self.tab_maint, text="Add maintenance task", padding=12)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        form.columnconfigure(1, weight=1)
        form.rowconfigure(6, weight=1)

        self.var_m_task = tk.StringVar(value="Oil change")
        self.var_m_last_date = tk.StringVar(value=today_str())
        self.var_m_last_miles = tk.StringVar(value="")
        self.var_m_interval_miles = tk.StringVar(value="3000")
        self.var_m_notes = tk.StringVar(value="")

        r = 0
        ttk.Label(form, text="Task").grid(row=r, column=0, sticky="w")
        ttk.Combobox(form, textvariable=self.var_m_task, values=MAINT_TYPES, state="readonly")\
            .grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(form, text="Last done date").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_m_last_date).grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(form, text="Last done mileage").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_m_last_miles).grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(form, text="Interval miles").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_m_interval_miles).grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(form, text="Notes").grid(row=r, column=0, sticky="nw", pady=(6, 0))
        mnotes_frame = ttk.Frame(form)
        mnotes_frame.grid(row=r, column=1, sticky="nsew", pady=(6, 0))
        mnotes_frame.rowconfigure(0, weight=1)
        mnotes_frame.columnconfigure(0, weight=1)

        self.txt_m_notes = tk.Text(mnotes_frame, wrap="word", height=10)
        self.txt_m_notes.grid(row=0, column=0, sticky="nsew")
        ms = ttk.Scrollbar(mnotes_frame, orient="vertical", command=self.txt_m_notes.yview)
        self.txt_m_notes.configure(yscrollcommand=ms.set)
        ms.grid(row=0, column=1, sticky="ns")
        r += 1

        btns = ttk.Frame(form)
        btns.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        ttk.Button(btns, text="Add task", command=self.add_maintenance).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(btns, text="Clear", command=self.clear_maintenance_form).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Right: maintenance list
        right = ttk.LabelFrame(self.tab_maint, text="Maintenance list", padding=12)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        columns = ("task", "last_date", "last_miles", "interval", "due_miles", "remaining", "notes")
        self.tree_maint = ttk.Treeview(right, columns=columns, show="headings", height=16)
        self.tree_maint.grid(row=1, column=0, sticky="nsew")

        heads = {
            "task": "Task",
            "last_date": "Last date",
            "last_miles": "Last miles",
            "interval": "Interval",
            "due_miles": "Due @",
            "remaining": "Remaining",
            "notes": "Notes",
        }
        for c, t in heads.items():
            self.tree_maint.heading(c, text=t)

        self.tree_maint.column("task", width=160, anchor="w")
        self.tree_maint.column("last_date", width=90, anchor="w")
        self.tree_maint.column("last_miles", width=85, anchor="e")
        self.tree_maint.column("interval", width=80, anchor="e")
        self.tree_maint.column("due_miles", width=85, anchor="e")
        self.tree_maint.column("remaining", width=95, anchor="e")
        self.tree_maint.column("notes", width=260, anchor="w")

        scroll = ttk.Scrollbar(right, orient="vertical", command=self.tree_maint.yview)
        self.tree_maint.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns")

        actions = ttk.Frame(right)
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for i in range(3):
            actions.columnconfigure(i, weight=1)

        ttk.Button(actions, text="Delete selected", command=self.delete_maintenance).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(actions, text="Mark done (updates last miles/date)", command=self.mark_maintenance_done).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(actions, text="Save now", command=lambda: self._save(force=True)).grid(row=0, column=2, sticky="ew", padx=(6, 0))

    # ---------------- Actions ----------------
    def set_current_mileage(self):
        s = self.var_current_mileage.get().strip()
        if not s:
            self.active_vehicle["current_mileage"] = None
            self._mark_dirty()
            self._save(force=False)
            self._refresh_maintenance_list()
            return
        try:
            miles = int(normalize_int(s))
        except ValueError:
            messagebox.showerror("Invalid mileage", "Current mileage should be a whole number (ex: 150000).")
            return
        self.active_vehicle["current_mileage"] = miles
        self._mark_dirty()
        self._save(force=False)
        self._refresh_maintenance_list()

    def clear_form(self):
        self.var_name.set("")
        self.var_category.set("Suspension")
        self.var_status.set("Planned")
        self.var_scope.set("Full car")
        self.var_date.set(today_str())
        self.var_mileage.set("")
        self.var_cost.set("")
        self.txt_quick_notes.delete("1.0", "end")

    def add_item(self):
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Missing info", "Name is required.")
            return

        mileage = self.var_mileage.get().strip()
        cost = self.var_cost.get().strip()

        if mileage:
            try:
                int(normalize_int(mileage))
            except ValueError:
                messagebox.showerror("Invalid mileage", "Mileage should be a whole number (ex: 150000).")
                return

        if cost:
            try:
                float(normalize_money(cost))
            except ValueError:
                messagebox.showerror("Invalid cost", "Cost should be a number (ex: 199.99).")
                return

        item = {
            "date": self.var_date.get().strip() or today_str(),
            "name": name,
            "category": self.var_category.get(),
            "status": self.var_status.get(),
            "scope": self.var_scope.get(),
            "mileage": mileage,
            "cost": cost,
            "notes": self.txt_quick_notes.get("1.0", "end").rstrip(),
            "attachments": [],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        self.items.append(item)
        self._mark_dirty()
        self._save(force=False)
        self.clear_form()
        self._refresh_mod_lists()

    def _sync_active_tree(self):
        # choose which tree selection buttons act on
        current_tab = self.mods_nb.index(self.mods_nb.select())
        self.active_mod_tree = self.tree_pipeline if current_tab == 0 else self.tree_installed

    def _get_selected_mod_index(self):
        self._sync_active_tree()
        sel = self.active_mod_tree.selection()
        if not sel or len(sel) != 1:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def edit_selected(self):
        idx = self._get_selected_mod_index()
        if idx is None or not (0 <= idx < len(self.items)):
            messagebox.showinfo("Select one item", "Select exactly one row to open the editor.")
            return

        original = self.items[idx]

        def on_save(updated: dict):
            self.items[idx] = updated
            self._mark_dirty()
            self._save(force=False)
            self._refresh_mod_lists()

        ItemEditor(self, original, on_save)

    def delete_selected(self):
        self._sync_active_tree()
        selected = self.active_mod_tree.selection()
        if not selected:
            messagebox.showinfo("Nothing selected", "Select one or more rows first.")
            return
        if not messagebox.askyesno("Delete", f"Delete {len(selected)} selected item(s)?"):
            return

        idxs = sorted([int(iid) for iid in selected], reverse=True)
        for i in idxs:
            if 0 <= i < len(self.items):
                self.items.pop(i)

        self._mark_dirty()
        self._save(force=False)
        self._refresh_mod_lists()

    def show_totals(self):
        total = 0.0
        counts = {"Planned": 0, "In Progress": 0, "Installed": 0}
        for m in self.items:
            st = (m.get("status") or "Installed").strip()
            if st not in counts:
                st = "Installed"
            counts[st] += 1

            c = str(m.get("cost", "")).strip()
            if not c:
                continue
            try:
                total += float(normalize_money(c))
            except ValueError:
                pass

        messagebox.showinfo(
            "Totals",
            f"Planned: {counts['Planned']}\nIn Progress: {counts['In Progress']}\nInstalled: {counts['Installed']}\n\n"
            f"Total spent (Cost field): ${total:,.2f}\nItems logged: {len(self.items)}"
        )

    # ---------------- Maintenance ----------------
    def clear_maintenance_form(self):
        self.var_m_task.set("Oil change")
        self.var_m_last_date.set(today_str())
        self.var_m_last_miles.set("")
        self.var_m_interval_miles.set("3000")
        self.txt_m_notes.delete("1.0", "end")

    def add_maintenance(self):
        task = self.var_m_task.get().strip()
        if not task:
            messagebox.showerror("Missing info", "Task is required.")
            return

        last_miles = self.var_m_last_miles.get().strip()
        interval = self.var_m_interval_miles.get().strip()

        if last_miles:
            try:
                int(normalize_int(last_miles))
            except ValueError:
                messagebox.showerror("Invalid", "Last done mileage must be a whole number.")
                return

        if interval:
            try:
                int(normalize_int(interval))
            except ValueError:
                messagebox.showerror("Invalid", "Interval miles must be a whole number.")
                return

        m = {
            "task": task,
            "last_date": self.var_m_last_date.get().strip() or today_str(),
            "last_miles": last_miles,
            "interval_miles": interval,
            "notes": self.txt_m_notes.get("1.0", "end").rstrip(),
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        self.maintenance.append(m)
        self._mark_dirty()
        self._save(force=False)
        self.clear_maintenance_form()
        self._refresh_maintenance_list()

    def _get_selected_maintenance_index(self):
        sel = self.tree_maint.selection()
        if not sel or len(sel) != 1:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def delete_maintenance(self):
        selected = self.tree_maint.selection()
        if not selected:
            messagebox.showinfo("Nothing selected", "Select one or more rows first.")
            return
        if not messagebox.askyesno("Delete", f"Delete {len(selected)} maintenance task(s)?"):
            return

        idxs = sorted([int(iid) for iid in selected], reverse=True)
        for i in idxs:
            if 0 <= i < len(self.maintenance):
                self.maintenance.pop(i)

        self._mark_dirty()
        self._save(force=False)
        self._refresh_maintenance_list()

    def mark_maintenance_done(self):
        idx = self._get_selected_maintenance_index()
        if idx is None or not (0 <= idx < len(self.maintenance)):
            messagebox.showinfo("Select one", "Select one maintenance row first.")
            return

        cur = self.active_vehicle.get("current_mileage")
        if cur is None:
            messagebox.showinfo("Set current mileage", "Set current mileage at the top first, then you can mark tasks done cleanly.")
            return

        self.maintenance[idx]["last_date"] = today_str()
        self.maintenance[idx]["last_miles"] = str(cur)
        self.maintenance[idx]["updated_at"] = now_iso()

        self._mark_dirty()
        self._save(force=False)
        self._refresh_maintenance_list()

    # ---------------- Refresh ----------------
    def _update_status(self):
        saved = self.last_saved_at if self.last_saved_at else "not yet (this session)"
        path = os.path.abspath(DATA_FILE)
        dirty = " | UNSAVED CHANGES" if self.dirty else ""
        cm = self.active_vehicle.get("current_mileage")
        cm_txt = f"{cm:,}" if isinstance(cm, int) else "—"
        self.status.config(
            text=f"Vehicle: {self.active_vehicle.get('year')} {self.active_vehicle.get('make')} {self.active_vehicle.get('model')} "
                 f"| Current miles: {cm_txt} | Items: {len(self.items)} | Maint: {len(self.maintenance)} "
                 f"| Last saved: {saved}{dirty} | File: {path}"
        )

    def _refresh_all(self):
        self._refresh_mod_lists()
        self._refresh_maintenance_list()
        self._update_status()

    def _refresh_mod_lists(self):
        q = self.var_search.get().strip().lower()

        # clear both
        for tree in (self.tree_pipeline, self.tree_installed):
            for item in tree.get_children():
                tree.delete(item)

        for idx, m in enumerate(self.items):
            status = (m.get("status") or "Installed").strip()
            if status not in STATUSES:
                status = "Installed"

            attachments = m.get("attachments", [])
            files_count = len(attachments) if isinstance(attachments, list) else 0

            notes = m.get("notes", "")
            notes_str = notes if isinstance(notes, str) else ""
            preview = notes_str.replace("\n", " ").strip()
            if len(preview) > 60:
                preview = preview[:60] + "…"

            haystack = " ".join([
                str(m.get("date", "")),
                str(m.get("name", "")),
                str(m.get("category", "")),
                status,
                str(m.get("scope", "")),
                str(m.get("mileage", "")),
                str(m.get("cost", "")),
                notes_str,
            ]).lower()

            if q and q not in haystack:
                continue

            row = (
                m.get("date", ""),
                m.get("name", ""),
                m.get("category", ""),
                status,
                m.get("scope", ""),
                m.get("mileage", ""),
                m.get("cost", ""),
                str(files_count),
                preview,
            )

            if status == "Installed":
                self.tree_installed.insert("", "end", iid=str(idx), values=row)
            else:
                self.tree_pipeline.insert("", "end", iid=str(idx), values=row)

        self._update_status()

    def _refresh_maintenance_list(self):
        for item in self.tree_maint.get_children():
            self.tree_maint.delete(item)

        cur = self.active_vehicle.get("current_mileage")
        for idx, m in enumerate(self.maintenance):
            last_miles = m.get("last_miles", "")
            interval = m.get("interval_miles", "")

            due_miles = ""
            remaining = ""
            try:
                if str(last_miles).strip() and str(interval).strip():
                    due_val = int(normalize_int(str(last_miles))) + int(normalize_int(str(interval)))
                    due_miles = f"{due_val:,}"
                    if isinstance(cur, int):
                        remaining_val = due_val - cur
                        remaining = f"{remaining_val:,}" if remaining_val >= 0 else f"OVERDUE {abs(remaining_val):,}"
            except Exception:
                pass

            notes = m.get("notes", "")
            notes_str = notes if isinstance(notes, str) else ""
            notes_preview = notes_str.replace("\n", " ").strip()
            if len(notes_preview) > 60:
                notes_preview = notes_preview[:60] + "…"

            self.tree_maint.insert("", "end", iid=str(idx), values=(
                m.get("task", ""),
                m.get("last_date", ""),
                m.get("last_miles", ""),
                m.get("interval_miles", ""),
                due_miles,
                remaining,
                notes_preview,
            ))

        self._update_status()


if __name__ == "__main__":
    app = ModTrackerApp()
    app.mainloop()
