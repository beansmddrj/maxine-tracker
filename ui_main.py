from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

import data_store
from models import (
    APP_TITLE,
    APP_VERSION,
    AUTOSAVE_EVERY_MS,
    CATEGORIES,
    STATUSES,
    SCOPES,
    MAINT_TYPES,
    today_str,
    now_iso,
    normalize_int,
    normalize_money,
)
from ui_editors import ItemEditor

# Optional calendar widget
try:
    from tkcalendar import DateEntry

    TKCAL_OK = True
except Exception:
    TKCAL_OK = False


def apply_car_friendly_ui(root: tk.Tk, settings: dict):
    ui_scale = float(settings.get("ui_scale", 1.45))
    font_family = settings.get("font_family", "Segoe UI")
    font_size = int(settings.get("font_size", 13))
    theme_name = settings.get("theme", "dark")

    root.tk.call("tk", "scaling", ui_scale)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Base font sizes (buttons slightly bigger)
    style.configure(".", font=(font_family, font_size))
    style.configure("TLabel", font=(font_family, font_size))
    style.configure("TEntry", padding=(10, 10), font=(font_family, font_size))
    style.configure("TCombobox", padding=(10, 8), font=(font_family, font_size))
    style.configure("TCheckbutton", font=(font_family, font_size))
    style.configure("TLabelframe.Label", font=(font_family, font_size, "bold"))
    style.configure("TNotebook.Tab", padding=(20, 12), font=(font_family, font_size, "bold"))
    style.configure("Treeview", rowheight=40, font=(font_family, max(11, font_size - 1)))
    style.configure("Treeview.Heading", font=(font_family, max(11, font_size - 1), "bold"))
    style.configure("TButton", padding=(16, 12), font=(font_family, font_size + 1, "bold"))

        # --- Theme colors (better looking + consistent) ---
    if theme_name == "dark":
        bg = "#0F1115"        # app background
        fg = "#E6EAF2"        # main text
        muted = "#AAB3C5"     # secondary text
        card = "#151926"      # frames/labelframes surface
        field_bg = "#0B0E14"  # entry-like surfaces
        border = "#2A3142"
        accent = "#4C8DFF"    # blue accent
        accent2 = "#2E6BFF"
        danger = "#FF4D4D"
        btn_bg = "#1A2133"
        btn_hover = "#232C44"
        btn_press = "#2B3656"
        select_bg = "#2E6BFF"
    else:
        bg = "#F4F6FA"
        fg = "#121620"
        muted = "#556070"
        card = "#FFFFFF"
        field_bg = "#FFFFFF"
        border = "#CCD3E0"
        accent = "#2E6BFF"
        accent2 = "#1F57E7"
        danger = "#D93025"
        btn_bg = "#E9EDF5"
        btn_hover = "#DDE4F2"
        btn_press = "#CFD8EB"
        select_bg = "#2E6BFF"

    # ---- Base surfaces ----
    style.configure("TFrame", background=bg)
    style.configure("TLabelframe", background=card, bordercolor=border, relief="solid")
    style.configure("TLabelframe.Label", background=card, foreground=fg)
    style.configure("TLabel", background=bg, foreground=fg)

    # Notebook
    style.configure("TNotebook", background=bg, borderwidth=0)
    style.configure("TNotebook.Tab", background=card, foreground=fg)
    style.map(
        "TNotebook.Tab",
        background=[("selected", bg), ("active", card)],
        foreground=[("selected", fg), ("active", fg)],
    )

    # ---- Inputs ----
    style.configure("TEntry", fieldbackground=field_bg, foreground=fg, bordercolor=border, relief="flat")
    style.configure("TCombobox", fieldbackground=field_bg, foreground=fg)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", field_bg)],
        foreground=[("readonly", fg)],
        background=[("readonly", field_bg)],
    )

    # Checkbutton (clam behaves better than default)
    style.configure("TCheckbutton", background=bg, foreground=fg)

    # ---- Buttons (THIS fixes white buttons) ----
    style.configure(
        "TButton",
        background=btn_bg,
        foreground=fg,
        bordercolor=border,
        focusthickness=0,
        focuscolor=border,
        relief="flat",
    )
    style.map(
        "TButton",
        background=[("active", btn_hover), ("pressed", btn_press), ("disabled", card)],
        foreground=[("disabled", muted)],
    )

    # Optional: Accent button style you can use for key actions
    style.configure(
        "Accent.TButton",
        background=accent,
        foreground="#FFFFFF",
        bordercolor=accent2,
        relief="flat",
    )
    style.map(
        "Accent.TButton",
        background=[("active", accent2), ("pressed", accent2), ("disabled", card)],
        foreground=[("disabled", muted)],
    )

    # ---- Treeview ----
    style.configure(
        "Treeview",
        background=card,
        fieldbackground=card,
        foreground=fg,
        bordercolor=border,
        relief="flat",
    )
    style.map("Treeview", background=[("selected", select_bg)], foreground=[("selected", "#FFFFFF")])

    style.configure("Treeview.Heading", background=bg, foreground=fg, relief="flat")
    style.map("Treeview.Heading", background=[("active", card)])

    # Root background for non-ttk
    root.configure(background=bg)



def make_date_widget(parent, textvariable: tk.StringVar):
    """
    Returns a calendar DateEntry if tkcalendar is installed,
    otherwise falls back to a normal Entry.
    Always writes YYYY-MM-DD into textvariable.
    """
    if TKCAL_OK:
        w = DateEntry(parent, date_pattern="yyyy-mm-dd", width=12)

        try:
            w.set_date(textvariable.get().strip() or today_str())
        except Exception:
            pass

        def sync_to_var(_e=None):
            try:
                textvariable.set(w.get_date().strftime("%Y-%m-%d"))
            except Exception:
                pass

        w.bind("<<DateEntrySelected>>", sync_to_var)
        sync_to_var()
        return w

    return ttk.Entry(parent, textvariable=textvariable)


class ModTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = data_store.load_settings()
        apply_car_friendly_ui(self, self.settings)
        self.tk.call("tk", "scaling", self._scale_windowed)

        
        self._scale_windowed = 1.45
        self._scale_fullscreen = 1.0  # TV-safe


        self.data = data_store.load_data()
        self.vehicle = self._get_active_vehicle()


        self.data = data_store.load_data()
        self.vehicle = self._get_active_vehicle()

        self.last_saved_at: str | None = None
        self.dirty: bool = False

        self.title(f"{APP_TITLE} — {self.vehicle.get('name','Vehicle')}")
        self.minsize(1180, 720)

        self._fullscreen = False
        self.bind("<F11>", lambda _e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda _e: self.exit_fullscreen())

        self._build_ui()
        if self.settings.get("car_mode"):
            # start fullscreen if enabled
            self._fullscreen = True
            self.attributes("-fullscreen", True)
        self._refresh_all()

        self._autosave_ms = int(self.settings.get("autosave_ms", AUTOSAVE_EVERY_MS))
        self.after(self._autosave_ms, self._autosave_tick)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- fullscreen ----------
    def toggle_fullscreen(self):
    self._fullscreen = not self._fullscreen
    self.attributes("-fullscreen", self._fullscreen)

    # TV-safe scaling in fullscreen
    if self._fullscreen:
        self.tk.call("tk", "scaling", self._scale_fullscreen)
    else:
        self.tk.call("tk", "scaling", self._scale_windowed)

    def exit_fullscreen(self):
    self._fullscreen = False
    self.attributes("-fullscreen", False)
    self.tk.call("tk", "scaling", self._scale_windowed)


    # ---------- data helpers ----------
    def _get_active_vehicle(self) -> dict:
        vid = self.data.get("active_vehicle_id")
        for v in self.data.get("vehicles", []):
            if v.get("id") == vid:
                return v
        return self.data["vehicles"][0]

    @property
    def items(self) -> list[dict]:
        return self.vehicle.setdefault("items", [])

    @property
    def maintenance(self) -> list[dict]:
        return self.vehicle.setdefault("maintenance", [])

    def _mark_dirty(self):
        self.dirty = True
        self._update_status()

    def _save(self, force: bool = False):
        if not self.dirty and not force:
            return
        data_store.save_data(self.data)
        self.last_saved_at = now_iso()
        self.dirty = False
        self._update_status()

    def _autosave_tick(self):
        self._save(force=False)
        self.after(self._autosave_ms, self._autosave_tick)


    def _on_close(self):
        self._save(force=True)
        self.destroy()

    # ---------- UI ----------
    def _build_ui(self):
        top = ttk.Frame(self, padding=(12, 12, 12, 8))
        top.pack(fill="x")

        ttk.Label(
            top,
            text=f"{APP_TITLE} — {self.vehicle.get('name','')}",
            font=("Segoe UI", 18, "bold"),
        ).pack(side="left")

        right = ttk.Frame(top)
        right.pack(side="right")

        ttk.Button(right, text="Fullscreen (F11)", command=self.toggle_fullscreen).pack(
            side="left", padx=(0, 10)
        )

        ttk.Label(right, text="Current mileage").pack(side="left", padx=(0, 6))
        self.var_current_mileage = tk.StringVar(
            value=""
            if self.vehicle.get("current_mileage") is None
            else str(self.vehicle.get("current_mileage"))
        )
        ttk.Entry(right, textvariable=self.var_current_mileage, width=10).pack(side="left")
        ttk.Button(right, text="Set", command=self.set_current_mileage).pack(
            side="left", padx=(6, 0)
        )

        self.main_nb = ttk.Notebook(self)
        self.tab_settings = ttk.Frame(self.main_nb)
        self.main_nb.add(self.tab_settings, text="Settings")
        self._build_settings_tab()

        self.main_nb.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_mods = ttk.Frame(self.main_nb)
        self.tab_maint = ttk.Frame(self.main_nb)
        self.main_nb.add(self.tab_mods, text="Mods & Repairs")
        self.main_nb.add(self.tab_maint, text="Maintenance")

        self._build_mods_tab()
        self._build_maintenance_tab()

        # --- Status bar (bottom): left status + right version/unsaved ---
        self.status_bar = ttk.Frame(self)
        self.status_bar.pack(fill="x", padx=12, pady=(0, 10))

        self.status_left = ttk.Label(self.status_bar, text="", anchor="w")
        self.status_left.pack(side="left", fill="x", expand=True)

        self.status_right = ttk.Label(self.status_bar, text="", anchor="e")
        self.status_right.pack(side="right")

    # ---------- Mods tab ----------
    def _build_mods_tab(self):
        self.tab_mods.columnconfigure(0, weight=1)
        self.tab_mods.columnconfigure(1, weight=2)
        self.tab_mods.rowconfigure(0, weight=1)

        form = ttk.LabelFrame(
            self.tab_mods, text="Quick add (mods/repairs)", padding=12
        )
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
        ttk.Entry(form, textvariable=self.var_name).grid(
            row=r, column=1, sticky="ew", pady=6
        )
        r += 1

        ttk.Label(form, text="Category").grid(row=r, column=0, sticky="w")
        ttk.Combobox(
            form,
            textvariable=self.var_category,
            values=CATEGORIES,
            state="readonly",
        ).grid(row=r, column=1, sticky="ew", pady=6)
        r += 1

        ttk.Label(form, text="Status").grid(row=r, column=0, sticky="w")
        ttk.Combobox(
            form,
            textvariable=self.var_status,
            values=STATUSES,
            state="readonly",
        ).grid(row=r, column=1, sticky="ew", pady=6)
        r += 1

        ttk.Label(form, text="Scope").grid(row=r, column=0, sticky="w")
        ttk.Combobox(
            form,
            textvariable=self.var_scope,
            values=SCOPES,
            state="readonly",
        ).grid(row=r, column=1, sticky="ew", pady=6)
        r += 1

        ttk.Label(form, text="Date").grid(row=r, column=0, sticky="w")
        self.date_add_widget = make_date_widget(form, self.var_date)
        self.date_add_widget.grid(row=r, column=1, sticky="w", pady=6)
        r += 1

        ttk.Label(form, text="Mileage").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_mileage).grid(
            row=r, column=1, sticky="ew", pady=6
        )
        r += 1

        ttk.Label(form, text="Cost ($)").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_cost).grid(
            row=r, column=1, sticky="ew", pady=6
        )
        r += 1

        ttk.Label(form, text="Notes (quick)").grid(
            row=r, column=0, sticky="nw", pady=(8, 0)
        )
        nf = ttk.Frame(form)
        nf.grid(row=r, column=1, sticky="nsew", pady=(8, 0))
        nf.rowconfigure(0, weight=1)
        nf.columnconfigure(0, weight=1)

        self.txt_quick_notes = tk.Text(nf, wrap="word", height=10, font=("Segoe UI", 14))
        self.txt_quick_notes.configure(bg="#0B0E14", fg="#E6EAF2", insertbackground="#E6EAF2",selectbackground="#2E6BFF", selectforeground="#FFFFFF")

        self.txt_quick_notes.grid(row=0, column=0, sticky="nsew")
        qs = ttk.Scrollbar(nf, orient="vertical", command=self.txt_quick_notes.yview)
        self.txt_quick_notes.configure(yscrollcommand=qs.set)
        qs.grid(row=0, column=1, sticky="ns")
        r += 1

        btns = ttk.Frame(form)
        btns.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        ttk.Button(btns, text="Add", command=self.add_item).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(btns, text="Clear", command=self.clear_mod_form).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )

        # Right side
        right = ttk.LabelFrame(self.tab_mods, text="Log", padding=12)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        sb = ttk.Frame(right)
        sb.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        sb.columnconfigure(1, weight=1)
        ttk.Label(sb, text="Search").grid(row=0, column=0, sticky="w")
        self.var_search = tk.StringVar()
        ent = ttk.Entry(sb, textvariable=self.var_search)
        ent.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        ent.bind("<KeyRelease>", lambda _e: self._refresh_mod_lists())

        self.mods_nb = ttk.Notebook(right)
        self.mods_nb.grid(row=1, column=0, sticky="ew")
        self.tab_pipeline = ttk.Frame(self.mods_nb, padding=(0, 6, 0, 0))
        self.tab_installed = ttk.Frame(self.mods_nb, padding=(0, 6, 0, 0))
        self.mods_nb.add(self.tab_pipeline, text="Pipeline (Planned / In Progress)")
        self.mods_nb.add(self.tab_installed, text="Installed")

        self.tree_pipeline = self._make_mod_tree(self.tab_pipeline)
        self.tree_installed = self._make_mod_tree(self.tab_installed)

        actions = ttk.Frame(right)
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        for i in range(4):
            actions.columnconfigure(i, weight=1)

        ttk.Button(actions, text="Open editor", command=self.edit_selected_mod).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(actions, text="Delete selected", command=self.delete_selected_mod).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        ttk.Button(actions, text="Show totals", command=self.show_mod_totals).grid(
            row=0, column=2, sticky="ew", padx=8
        )
        ttk.Button(actions, text="Save now", command=lambda: self._save(force=True)).grid(
            row=0, column=3, sticky="ew", padx=(8, 0)
        )

    def _make_mod_tree(self, parent) -> ttk.Treeview:
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        cols = ("date", "name", "category", "status", "scope", "mileage", "cost", "files", "notes")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=14)
        tree.grid(row=0, column=0, sticky="nsew")

        headers = {
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
        for c, t in headers.items():
            tree.heading(c, text=t)

        tree.column("date", width=105, anchor="w")
        tree.column("name", width=220, anchor="w")
        tree.column("category", width=120, anchor="w")
        tree.column("status", width=120, anchor="w")
        tree.column("scope", width=140, anchor="w")
        tree.column("mileage", width=95, anchor="e")
        tree.column("cost", width=90, anchor="e")
        tree.column("files", width=70, anchor="center")
        tree.column("notes", width=320, anchor="w")

        tree.bind("<Double-1>", lambda _e: self.edit_selected_mod())

        s = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=s.set)
        s.grid(row=0, column=1, sticky="ns")
        return tree

    def clear_mod_form(self):
        self.var_name.set("")
        self.var_category.set("Suspension")
        self.var_status.set("Planned")
        self.var_scope.set("Full car")
        self.var_date.set(today_str())
        if TKCAL_OK:
            try:
                self.date_add_widget.set_date(self.var_date.get())
            except Exception:
                pass
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
                messagebox.showerror(
                    "Invalid mileage", "Mileage should be a whole number (ex: 150000)."
                )
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
        self.clear_mod_form()
        self._refresh_mod_lists()

    def _active_mod_tree(self) -> ttk.Treeview:
        return self.tree_installed if self.mods_nb.index(self.mods_nb.select()) == 1 else self.tree_pipeline

    def _selected_mod_index(self) -> int | None:
        tree = self._active_mod_tree()
        sel = tree.selection()
        if not sel or len(sel) != 1:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def edit_selected_mod(self):
        idx = self._selected_mod_index()
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

    def delete_selected_mod(self):
        tree = self._active_mod_tree()
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Nothing selected", "Select one or more rows first.")
            return
        if not messagebox.askyesno("Delete", f"Delete {len(selected)} selected item(s)?"):
            return

        idxs = sorted([int(i) for i in selected], reverse=True)
        for i in idxs:
            if 0 <= i < len(self.items):
                self.items.pop(i)

        self._mark_dirty()
        self._save(force=False)
        self._refresh_mod_lists()

    def show_mod_totals(self):
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
            f"Total (Cost field): ${total:,.2f}\nItems logged: {len(self.items)}",
        )

    def _refresh_mod_lists(self):
        q = self.var_search.get().strip().lower()

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
            if len(preview) > 80:
                preview = preview[:80] + "…"

            hay = " ".join(
                [
                    str(m.get("date", "")),
                    str(m.get("name", "")),
                    str(m.get("category", "")),
                    status,
                    str(m.get("scope", "")),
                    str(m.get("mileage", "")),
                    str(m.get("cost", "")),
                    notes_str,
                ]
            ).lower()

            if q and q not in hay:
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

    # ---------- Maintenance tab ----------
    def _build_maintenance_tab(self):
        self.tab_maint.columnconfigure(0, weight=1)
        self.tab_maint.columnconfigure(1, weight=2)
        self.tab_maint.rowconfigure(0, weight=1)

        form = ttk.LabelFrame(self.tab_maint, text="Add maintenance task", padding=12)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        form.columnconfigure(1, weight=1)
        form.rowconfigure(6, weight=1)

        self.var_m_task = tk.StringVar(value="Oil change")
        self.var_m_last_date = tk.StringVar(value=today_str())
        self.var_m_last_miles = tk.StringVar(value="")
        self.var_m_interval_miles = tk.StringVar(value="3000")

        r = 0
        ttk.Label(form, text="Task").grid(row=r, column=0, sticky="w")
        ttk.Combobox(
            form, textvariable=self.var_m_task, values=MAINT_TYPES, state="readonly"
        ).grid(row=r, column=1, sticky="ew", pady=6)
        r += 1

        ttk.Label(form, text="Last done date").grid(row=r, column=0, sticky="w")
        self.maint_date_widget = make_date_widget(form, self.var_m_last_date)
        self.maint_date_widget.grid(row=r, column=1, sticky="w", pady=6)
        r += 1

        ttk.Label(form, text="Last done mileage").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_m_last_miles).grid(
            row=r, column=1, sticky="ew", pady=6
        )
        r += 1

        ttk.Label(form, text="Interval miles").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_m_interval_miles).grid(
            row=r, column=1, sticky="ew", pady=6
        )
        r += 1

        ttk.Label(form, text="Notes").grid(row=r, column=0, sticky="nw", pady=(8, 0))
        nf = ttk.Frame(form)
        nf.grid(row=r, column=1, sticky="nsew", pady=(8, 0))
        nf.rowconfigure(0, weight=1)
        nf.columnconfigure(0, weight=1)

        self.txt_m_notes = tk.Text(nf, wrap="word", height=10, font=("Segoe UI", 14))
        self.txt_quick_notes.configure(bg="#0B0E14", fg="#E6EAF2", insertbackground="#E6EAF2",selectbackground="#2E6BFF", selectforeground="#FFFFFF")
        self.txt_m_notes.grid(row=0, column=0, sticky="nsew")
        s = ttk.Scrollbar(nf, orient="vertical", command=self.txt_m_notes.yview)
        self.txt_m_notes.configure(yscrollcommand=s.set)
        s.grid(row=0, column=1, sticky="ns")
        r += 1

        btns = ttk.Frame(form)
        btns.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        ttk.Button(btns, text="Add task", command=self.add_maintenance).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(btns, text="Clear", command=self.clear_maintenance_form).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )

        right = ttk.LabelFrame(self.tab_maint, text="Maintenance list", padding=12)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        cols = ("task", "last_date", "last_miles", "interval", "due_miles", "remaining", "notes")
        self.tree_maint = ttk.Treeview(right, columns=cols, show="headings", height=16)
        self.tree_maint.grid(row=1, column=0, sticky="nsew")

        headers = {
            "task": "Task",
            "last_date": "Last date",
            "last_miles": "Last miles",
            "interval": "Interval",
            "due_miles": "Due @",
            "remaining": "Remaining",
            "notes": "Notes",
        }
        for c, t in headers.items():
            self.tree_maint.heading(c, text=t)

        self.tree_maint.column("task", width=190, anchor="w")
        self.tree_maint.column("last_date", width=110, anchor="w")
        self.tree_maint.column("last_miles", width=110, anchor="e")
        self.tree_maint.column("interval", width=110, anchor="e")
        self.tree_maint.column("due_miles", width=110, anchor="e")
        self.tree_maint.column("remaining", width=140, anchor="e")
        self.tree_maint.column("notes", width=360, anchor="w")

        vs = ttk.Scrollbar(right, orient="vertical", command=self.tree_maint.yview)
        self.tree_maint.configure(yscrollcommand=vs.set)
        vs.grid(row=1, column=1, sticky="ns")

        actions = ttk.Frame(right)
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        for i in range(3):
            actions.columnconfigure(i, weight=1)

        ttk.Button(actions, text="Delete selected", command=self.delete_maintenance).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(
            actions, text="Mark done (uses current mileage)", command=self.mark_maintenance_done
        ).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(actions, text="Save now", command=lambda: self._save(force=True)).grid(
            row=0, column=2, sticky="ew", padx=(8, 0)
        )

    def clear_maintenance_form(self):
        self.var_m_task.set("Oil change")
        self.var_m_last_date.set(today_str())
        if TKCAL_OK:
            try:
                self.maint_date_widget.set_date(self.var_m_last_date.get())
            except Exception:
                pass
        self.var_m_last_miles.set("")
        self.var_m_interval_miles.set("3000")
        self.txt_m_notes.delete("1.0", "end")
        self.txt_quick_notes.configure(bg="#0B0E14", fg="#E6EAF2", insertbackground="#E6EAF2",selectbackground="#2E6BFF", selectforeground="#FFFFFF")

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

    def delete_maintenance(self):
        sel = self.tree_maint.selection()
        if not sel:
            messagebox.showinfo("Nothing selected", "Select one or more rows first.")
            return
        if not messagebox.askyesno("Delete", f"Delete {len(sel)} maintenance task(s)?"):
            return

        idxs = sorted([int(i) for i in sel], reverse=True)
        for i in idxs:
            if 0 <= i < len(self.maintenance):
                self.maintenance.pop(i)

        self._mark_dirty()
        self._save(force=False)
        self._refresh_maintenance_list()

    def mark_maintenance_done(self):
        sel = self.tree_maint.selection()
        if not sel or len(sel) != 1:
            messagebox.showinfo("Select one", "Select one maintenance row first.")
            return
        idx = int(sel[0])

        cur = self.vehicle.get("current_mileage")
        if cur is None:
            messagebox.showinfo("Set current mileage", "Set current mileage at the top first.")
            return

        self.maintenance[idx]["last_date"] = today_str()
        self.maintenance[idx]["last_miles"] = str(cur)
        self.maintenance[idx]["updated_at"] = now_iso()

        self._mark_dirty()
        self._save(force=False)
        self._refresh_maintenance_list()

    # ---------- current mileage ----------
    def set_current_mileage(self):
        s = self.var_current_mileage.get().strip()
        if not s:
            self.vehicle["current_mileage"] = None
            self._mark_dirty()
            self._save(force=False)
            self._refresh_maintenance_list()
            return

        try:
            miles = int(normalize_int(s))
        except ValueError:
            messagebox.showerror(
                "Invalid mileage", "Current mileage should be a whole number (ex: 150000)."
            )
            return

        self.vehicle["current_mileage"] = miles
        self._mark_dirty()
        self._save(force=False)
        self._refresh_maintenance_list()

    # ---------- refresh ----------
    def _refresh_maintenance_list(self):
        for item in self.tree_maint.get_children():
            self.tree_maint.delete(item)

        cur = self.vehicle.get("current_mileage")
        for idx, m in enumerate(self.maintenance):
            last_miles = m.get("last_miles", "")
            interval = m.get("interval_miles", "")

            due_miles = ""
            remaining = ""
            try:
                if str(last_miles).strip() and str(interval).strip():
                    due_val = int(normalize_int(str(last_miles))) + int(
                        normalize_int(str(interval))
                    )
                    due_miles = f"{due_val:,}"
                    if isinstance(cur, int):
                        remaining_val = due_val - cur
                        remaining = (
                            f"{remaining_val:,}"
                            if remaining_val >= 0
                            else f"OVERDUE {abs(remaining_val):,}"
                        )
            except Exception:
                pass

            notes = m.get("notes", "")
            notes_str = notes if isinstance(notes, str) else ""
            preview = notes_str.replace("\n", " ").strip()
            if len(preview) > 80:
                preview = preview[:80] + "…"

            self.tree_maint.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    m.get("task", ""),
                    m.get("last_date", ""),
                    m.get("last_miles", ""),
                    m.get("interval_miles", ""),
                    due_miles,
                    remaining,
                    preview,
                ),
            )

        self._update_status()

    def _update_status(self):
        saved = self.last_saved_at if self.last_saved_at else "not yet (this session)"
        cm = self.vehicle.get("current_mileage")
        cm_txt = f"{cm:,}" if isinstance(cm, int) else "—"

        # left side (your original status text)
        self.status_left.config(
            text=f"Vehicle: {self.vehicle.get('year')} {self.vehicle.get('make')} {self.vehicle.get('model')} "
                 f"| Current miles: {cm_txt} | Items: {len(self.items)} | Maint: {len(self.maintenance)} "
                 f"| Last saved: {saved}"
        )

        # right side (version + unsaved indicator)
        right_text = f"v{APP_VERSION}"
        if self.dirty:
            right_text += "  •  UNSAVED"
        self.status_right.config(text=right_text)

    def _refresh_all(self):
        self._refresh_mod_lists()
        self._refresh_maintenance_list()
        self._update_status()

    def _build_settings_tab(self):
        self.tab_settings.columnconfigure(0, weight=1)

        box = ttk.LabelFrame(self.tab_settings, text="App settings", padding=12)
        box.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        box.columnconfigure(1, weight=1)

        # Theme
        ttk.Label(box, text="Theme").grid(row=0, column=0, sticky="w", pady=8)
        self.var_theme = tk.StringVar(value=self.settings.get("theme", "dark"))
        ttk.Combobox(
            box,
            textvariable=self.var_theme,
            values=["dark", "light"],
            state="readonly",
            width=18,
        ).grid(row=0, column=1, sticky="w", pady=8)

        # UI scale presets
        ttk.Label(box, text="UI scale").grid(row=1, column=0, sticky="w", pady=8)
        current_scale = float(self.settings.get("ui_scale", 1.45))
        # store as strings to avoid float weirdness in combobox
        scale_choices = ["1.15", "1.30", "1.45", "1.60", "1.75"]
        self.var_scale = tk.StringVar(value=f"{current_scale:.2f}" if f"{current_scale:.2f}" in scale_choices else "1.45")
        ttk.Combobox(
            box,
            textvariable=self.var_scale,
            values=scale_choices,
            state="readonly",
            width=18,
        ).grid(row=1, column=1, sticky="w", pady=8)

        # Autosave interval
        ttk.Label(box, text="Autosave").grid(row=2, column=0, sticky="w", pady=8)
        # show friendly labels but store ms
        autosave_map = {
            "5 seconds": 5_000,
            "10 seconds": 10_000,
            "20 seconds": 20_000,
            "30 seconds": 30_000,
            "60 seconds": 60_000,
        }
        inv = {v: k for k, v in autosave_map.items()}
        cur_ms = int(self.settings.get("autosave_ms", 20_000))
        self.var_autosave = tk.StringVar(value=inv.get(cur_ms, "20 seconds"))
        ttk.Combobox(
            box,
            textvariable=self.var_autosave,
            values=list(autosave_map.keys()),
            state="readonly",
            width=18,
        ).grid(row=2, column=1, sticky="w", pady=8)

        # Car mode
        ttk.Label(box, text="Car mode").grid(row=3, column=0, sticky="w", pady=8)
        self.var_car_mode = tk.BooleanVar(value=bool(self.settings.get("car_mode", False)))
        ttk.Checkbutton(
            box,
            text="Fullscreen on startup + touch-friendly behavior",
            variable=self.var_car_mode,
        ).grid(row=3, column=1, sticky="w", pady=8)

        ttk.Separator(box).grid(row=4, column=0, columnspan=2, sticky="ew", pady=14)

        hint = ttk.Label(
            box,
            text="Tip: Theme + scale changes are most stable after a restart.",
        )
        hint.grid(row=5, column=0, columnspan=2, sticky="w")

        btns = ttk.Frame(box)
        btns.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        btns.columnconfigure(0, weight=1)
        ttk.Button(btns, text="Save settings", command=self._save_settings_only).grid(row=0, column=1, sticky="e", padx=(0, 10))
        ttk.Button(btns, text="Apply + Restart app", command=self._apply_settings_and_restart).grid(row=0, column=2, sticky="e")

        # keep mapping available in other methods
        self._autosave_label_to_ms = autosave_map


    def _save_settings_only(self):
        # update in-memory
        self.settings["theme"] = self.var_theme.get()
        try:
            self.settings["ui_scale"] = float(self.var_scale.get())
        except Exception:
            self.settings["ui_scale"] = 1.45

        label = self.var_autosave.get()
        self.settings["autosave_ms"] = int(self._autosave_label_to_ms.get(label, 20_000))
        self.settings["car_mode"] = bool(self.var_car_mode.get())

        data_store.save_settings(self.settings)

        # apply autosave interval live (safe)
        self._autosave_ms = int(self.settings.get("autosave_ms", self._autosave_ms))
        messagebox.showinfo("Saved", "Settings saved.\n\nFor best results, use Apply + Restart for theme/scale.")


    def _apply_settings_and_restart(self):
        self._save_settings_only()
        # restart is the cleanest way to apply theme/scaling without widget weirdness
        import os, sys
        try:
            self._save(force=True)
        except Exception:
            pass
        python = sys.executable
        os.execl(python, python, *sys.argv)
