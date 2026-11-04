"""Small reusable ttk views."""
import tkinter as tk
from tkinter import ttk

BG = "#101820"
PANEL = "#1b2733"
FG = "#e5edf5"
MUTED = "#a5b8c8"
CYAN = "#40d9e6"


def heading(parent, title, description):
    ttk.Label(parent, text=title, style="Title.TLabel").pack(anchor="w", pady=(0, 8))
    ttk.Label(parent, text=description, wraplength=850, style="Muted.TLabel").pack(anchor="w", pady=(0, 16))


def text_view(parent):
    frame = ttk.Frame(parent)
    text = tk.Text(frame, bg=PANEL, fg=FG, insertbackground=FG, relief="flat",
                   font=("DejaVu Sans Mono", 10), wrap="word", padx=12, pady=12,
                   height=6, state="disabled")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    text.pack(fill="both", expand=True)
    return frame, text


def set_text(widget, content):
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", content)
    widget.configure(state="disabled")


def table(parent, columns):
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=[key for key, title, width in columns], show="headings")
    for key, title, width in columns:
        tree.heading(key, text=title)
        tree.column(key, width=width, minwidth=80, stretch=True)
    vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    return frame, tree
