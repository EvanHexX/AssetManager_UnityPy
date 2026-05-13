# asset_patcher/ui/tsv_editor.py
# 설명:
# metadata TSV를 확인/수정하기 위한 간단한 Tkinter 관리 화면.

from __future__ import annotations

import csv
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TsvTableEditor(ttk.Frame):
    """
    하나의 TSV 파일을 Treeview + 입력 폼으로 편집한다.
    """

    def __init__(self, master: tk.Misc, title: str, path: Path) -> None:
        super().__init__(master)
        self.title = title
        self.path = path
        self.columns: list[str] = []
        self.rows: list[dict[str, str]] = []
        self.entries: dict[str, ttk.Entry] = {}
        self.selected_index: int | None = None

        self._build()
        self.load()

    def _build(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=8)

        self.path_var = tk.StringVar(value=str(self.path))
        ttk.Entry(toolbar, textvariable=self.path_var).pack(side="left", fill="x", expand=True)
        ttk.Button(toolbar, text="Open", command=self.open_file).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Reload", command=self.load).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Save", command=self.save).pack(side="left", padx=(6, 0))

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=8)

        self.tree = ttk.Treeview(table_frame, show="headings", selectmode="browse")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.form = ttk.LabelFrame(self, text=f"{self.title} Row")
        self.form.pack(fill="x", padx=8, pady=8)

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(actions, text="New", command=self.clear_form).pack(side="left")
        ttk.Button(actions, text="Add", command=self.add_row).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Update", command=self.update_row).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Delete", command=self.delete_row).pack(side="left", padx=(6, 0))

    def open_file(self) -> None:
        selected = filedialog.askopenfilename(
            title=f"Open {self.title} TSV",
            filetypes=[("TSV files", "*.tsv"), ("All files", "*.*")],
            initialdir=str(self.path.parent),
        )

        if selected:
            self.path = Path(selected)
            self.path_var.set(str(self.path))
            self.load()

    def load(self) -> None:
        self.path = Path(self.path_var.get())

        if not self.path.exists():
            messagebox.showerror("Load failed", f"파일이 없습니다:\n{self.path}")
            return

        with self.path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            self.columns = list(reader.fieldnames or [])
            self.rows = [{key: row.get(key, "") for key in self.columns} for row in reader]

        self.selected_index = None
        self._rebuild_tree()
        self._rebuild_form()
        self.clear_form()

    def save(self) -> None:
        if not self.columns:
            messagebox.showerror("Save failed", "저장할 컬럼이 없습니다.")
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)

        with self.path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.columns, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(self.rows)

        messagebox.showinfo("Saved", f"저장했습니다:\n{self.path}")

    def _rebuild_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = self.columns

        for column in self.columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=max(90, min(220, len(column) * 14)), stretch=True)

        for index, row in enumerate(self.rows):
            values = [row.get(column, "") for column in self.columns]
            self.tree.insert("", "end", iid=str(index), values=values)

    def _rebuild_form(self) -> None:
        for child in self.form.winfo_children():
            child.destroy()

        self.entries = {}

        for index, column in enumerate(self.columns):
            row = index // 4
            pair_col = (index % 4) * 2
            ttk.Label(self.form, text=column).grid(row=row, column=pair_col, sticky="w", padx=6, pady=4)
            entry = ttk.Entry(self.form)
            entry.grid(row=row, column=pair_col + 1, sticky="ew", padx=6, pady=4)
            self.form.columnconfigure(pair_col + 1, weight=1)
            self.entries[column] = entry

    def on_select(self, _event: tk.Event) -> None:
        selection = self.tree.selection()

        if not selection:
            return

        self.selected_index = int(selection[0])
        row = self.rows[self.selected_index]
        self._set_form(row)

    def clear_form(self) -> None:
        self.selected_index = None
        self.tree.selection_remove(self.tree.selection())
        self._set_form({column: "" for column in self.columns})

    def add_row(self) -> None:
        row = self._get_form()
        self.rows.append(row)
        self._rebuild_tree()
        self.tree.selection_set(str(len(self.rows) - 1))

    def update_row(self) -> None:
        if self.selected_index is None:
            messagebox.showwarning("Update", "수정할 row를 먼저 선택하세요.")
            return

        self.rows[self.selected_index] = self._get_form()
        self._rebuild_tree()
        self.tree.selection_set(str(self.selected_index))

    def delete_row(self) -> None:
        if self.selected_index is None:
            messagebox.showwarning("Delete", "삭제할 row를 먼저 선택하세요.")
            return

        if not messagebox.askyesno("Delete", "선택한 row를 삭제할까요?"):
            return

        del self.rows[self.selected_index]
        self.selected_index = None
        self._rebuild_tree()
        self.clear_form()

    def _set_form(self, row: dict[str, str]) -> None:
        for column, entry in self.entries.items():
            entry.delete(0, "end")
            entry.insert(0, row.get(column, ""))

    def _get_form(self) -> dict[str, str]:
        return {column: entry.get().strip() for column, entry in self.entries.items()}


def run_tsv_editor() -> None:
    root = tk.Tk()
    root.title("AssetManager UnityPy Metadata")
    root.geometry("1280x720")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    tabs = [
        ("Outfit Textures", PROJECT_ROOT / "metadata" / "data.tsv"),
        ("UI Textures", PROJECT_ROOT / "metadata" / "ui_textures.tsv"),
    ]

    for title, path in tabs:
        frame = TsvTableEditor(notebook, title=title, path=path)
        notebook.add(frame, text=title)

    root.mainloop()
