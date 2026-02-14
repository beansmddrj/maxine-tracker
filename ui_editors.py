from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import data_store
from models import CATEGORIES, STATUSES, SCOPES, today_str, now_iso, normalize_int, normalize_money, ASSETS_DIR

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False

# Optional calendar widget
try:
    from tkcalendar import DateEntry
    TKCAL_OK = True
except Exception:
    TKCAL_OK = False


def open_file_with_default_app(path: str) -> None:
    if not path or not os.path.exists(path):
        raise FileNotFoundError("File not found.")
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


def unique_dest_path(dest_folder: Path, src_path: str) -> Path:
    src = Path(src_path)
    name = src.stem
    ext = src.suffix
    stamp = now_iso().replace(":", "").replace(" ", "_").replace("-", "")
    candidate = dest_folder / f"{name}_{stamp}{ext}"
    i = 1
    while candidate.exists():
        candidate = dest_folder / f"{name}_{stamp}_{i}{ext}"
        i += 1
    return candidate


def make_date_widget(parent, textvariable: tk.StringVar):
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


class ItemEditor(tk.Toplevel):
    def __init__(self, parent: tk.Tk, item: dict, on_save):
        super().__init__(parent)
        self.title("Edit mod / repair")
        self.minsize(1040, 720)
        self.on_save = on_save
        self.item = dict(item)

        self.var_name = tk.StringVar(value=self.item.get("name", ""))
        self.var_category = tk.StringVar(value=self.item.get("category", "Suspension"))
        self.var_status = tk.StringVar(value=self.item.get("status", "Planned"))
        self.var_scope = tk.StringVar(value=self.item.get("scope", "Full car"))
        self.var_date = tk.StringVar(value=self.item.get("date", today_str()))
        self.var_mileage = tk.StringVar(value=str(self.item.get("mileage", "")))
        self.var_cost = tk.StringVar(value=str(self.item.get("cost", "")))
        self.var_copy_assets = tk.BooleanVar(value=True)

        self.attachments = self.item.get("attachments", [])
        if not isinstance(self.attachments, list):
            self.attachments = []

        self._preview_img = None

        self._build_ui()

        notes = self.item.get("notes", "")
        self.txt_notes.insert("1.0", notes if isinstance(notes, str) else "")
        # after self.txt_notes created
        self.txt_notes.configure(
            bg="#0B0E14", fg="#E6EAF2", insertbackground="#E6EAF2",
            selectbackground="#2E6BFF", selectforeground="#FFFFFF"
        )

        # after self.lst_files created
        self.lst_files.configure(
            bg="#0B0E14", fg="#E6EAF2",
            selectbackground="#2E6BFF", selectforeground="#FFFFFF"
        )

        self._refresh_attachments_list()
        self._update_preview()

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
        ttk.Label(header, text="Mod / Repair Editor", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w")
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
        ttk.Entry(tab_details, textvariable=self.var_name).grid(row=r, column=1, sticky="ew", pady=8)
        r += 1

        ttk.Label(tab_details, text="Category").grid(row=r, column=0, sticky="w")
        ttk.Combobox(tab_details, textvariable=self.var_category, values=CATEGORIES, state="readonly")\
            .grid(row=r, column=1, sticky="ew", pady=8)
        r += 1

        ttk.Label(tab_details, text="Status").grid(row=r, column=0, sticky="w")
        ttk.Combobox(tab_details, textvariable=self.var_status, values=STATUSES, state="readonly")\
            .grid(row=r, column=1, sticky="ew", pady=8)
        r += 1

        ttk.Label(tab_details, text="Scope (side/area)").grid(row=r, column=0, sticky="w")
        ttk.Combobox(tab_details, textvariable=self.var_scope, values=SCOPES, state="readonly")\
            .grid(row=r, column=1, sticky="ew", pady=8)
        r += 1

        ttk.Label(tab_details, text="Date").grid(row=r, column=0, sticky="w")
        self.date_edit_widget = make_date_widget(tab_details, self.var_date)
        self.date_edit_widget.grid(row=r, column=1, sticky="w", pady=8)
        r += 1

        ttk.Label(tab_details, text="Mileage").grid(row=r, column=0, sticky="w")
        ttk.Entry(tab_details, textvariable=self.var_mileage).grid(row=r, column=1, sticky="ew", pady=8)
        r += 1

        ttk.Label(tab_details, text="Cost ($)").grid(row=r, column=0, sticky="w")
        ttk.Entry(tab_details, textvariable=self.var_cost).grid(row=r, column=1, sticky="ew", pady=8)
        r += 1

        ttk.Separator(tab_details).grid(row=r, column=0, columnspan=2, sticky="ew", pady=14)
        r += 1

        ttk.Checkbutton(
            tab_details,
            text=f"Copy uploaded files into {ASSETS_DIR} (recommended)",
            variable=self.var_copy_assets
        ).grid(row=r, column=0, columnspan=2, sticky="w")

        # Notes
        tab_notes.rowconfigure(0, weight=1)
        tab_notes.columnconfigure(0, weight=1)

        nf = ttk.Frame(tab_notes)
        nf.grid(row=0, column=0, sticky="nsew")
        nf.rowconfigure(0, weight=1)
        nf.columnconfigure(0, weight=1)

        self.txt_notes = tk.Text(nf, wrap="word", font=("Segoe UI", 15))
        self.txt_notes.grid(row=0, column=0, sticky="nsew")
        ns = ttk.Scrollbar(nf, orient="vertical", command=self.txt_notes.yview)
        self.txt_notes.configure(yscrollcommand=ns.set)
        ns.grid(row=0, column=1, sticky="ns")

        # Files
        tab_files.rowconfigure(1, weight=1)
        tab_files.rowconfigure(3, weight=1)
        tab_files.columnconfigure(0, weight=1)

        ttk.Label(tab_files, text="Select a file to preview (double-click opens it)").grid(row=0, column=0, sticky="w")

        fa = ttk.Frame(tab_files)
        fa.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        fa.rowconfigure(0, weight=1)
        fa.columnconfigure(0, weight=1)

        self.lst_files = tk.Listbox(fa, font=("Segoe UI", 14))
        self.lst_files.grid(row=0, column=0, sticky="nsew")
        fs = ttk.Scrollbar(fa, orient="vertical", command=self.lst_files.yview)
        self.lst_files.configure(yscrollcommand=fs.set)
        fs.grid(row=0, column=1, sticky="ns")

        self.lst_files.bind("<<ListboxSelect>>", lambda _e: self._update_preview())
        self.lst_files.bind("<Double-1>", lambda _e: self._open_selected())

        br = ttk.Frame(tab_files)
        br.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        for i in range(5):
            br.columnconfigure(i, weight=1)

        ttk.Button(br, text="Add Photo(s)", command=lambda: self._add_files("Photo")).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(br, text="Add Receipt(s)", command=lambda: self._add_files("Receipt")).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(br, text="Add File(s)", command=lambda: self._add_files("File")).grid(row=0, column=2, sticky="ew", padx=8)
        ttk.Button(br, text="Open", command=self._open_selected).grid(row=0, column=3, sticky="ew", padx=8)
        ttk.Button(br, text="Remove", command=self._remove_selected).grid(row=0, column=4, sticky="ew", padx=(8, 0))

        preview = ttk.LabelFrame(tab_files, text="Preview", padding=10)
        preview.grid(row=3, column=0, sticky="nsew", pady=(14, 0))
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(0, weight=1)

        self.preview_label = ttk.Label(preview, text="Select a photo to preview", anchor="center")
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        bottom = ttk.Frame(outer)
        bottom.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        bottom.columnconfigure(0, weight=1)
        ttk.Button(bottom, text="Save changes", command=self._save).grid(row=0, column=1, sticky="e", padx=(0, 10))
        ttk.Button(bottom, text="Cancel", command=self.destroy).grid(row=0, column=2, sticky="e")

    def _refresh_attachments_list(self):
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
        assets_folder = data_store.assets_dir()

        for p in paths:
            p = str(p)
            final_path = p

            if copy_into_assets:
                try:
                    dest = unique_dest_path(assets_folder, p)
                    shutil.copy2(p, dest)
                    final_path = str(dest)
                except Exception as e:
                    messagebox.showwarning(
                        "Copy failed",
                        f"Could not copy:\n{p}\n\nReason: {e}\n\nLinking original instead.",
                        parent=self
                    )
                    final_path = p

            self.attachments.append({
                "kind": kind,
                "path": final_path,
                "label": os.path.basename(final_path),
                "added_at": now_iso(),
            })

        self._refresh_attachments_list()
        self._update_preview()

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
        if not messagebox.askyesno("Remove", f"Remove attachment:\n{label}\n\n(Not deleting file from disk.)", parent=self):
            return
        self.attachments.pop(idx)
        self._refresh_attachments_list()
        self._update_preview()

    def _is_image_file(self, path: str) -> bool:
        ext = os.path.splitext(path.lower())[1]
        return ext in [".png", ".gif", ".jpg", ".jpeg", ".bmp", ".webp"]

    def _update_preview(self):
        idx = self._sel_index()
        if idx is None:
            self.preview_label.config(text="Select a photo to preview", image="")
            self._preview_img = None
            return

        att = self.attachments[idx]
        path = att.get("path", "")

        if not path or not os.path.exists(path):
            self.preview_label.config(text="File missing", image="")
            self._preview_img = None
            return

        if not self._is_image_file(path):
            self.preview_label.config(text="Not an image file", image="")
            self._preview_img = None
            return

        try:
            if PIL_OK:
                img = Image.open(path)
                img.thumbnail((900, 520))
                tk_img = ImageTk.PhotoImage(img)
            else:
                tk_img = tk.PhotoImage(file=path)
            self._preview_img = tk_img
            self.preview_label.config(image=tk_img, text="")
        except Exception:
            msg = "Preview failed."
            if not PIL_OK:
                msg += "\nInstall Pillow (Tools → Manage packages → pillow) for JPG/JPEG."
            self.preview_label.config(text=msg, image="")
            self._preview_img = None

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
