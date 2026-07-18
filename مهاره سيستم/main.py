"""
مهاره سيستم — Tkinter Application
برنامج مستقل بنفس أسلوب STC_System القديم
يحتوي على 4 وحدات: الإهمال / أخطاء النظام / عملاء مستهدفة / توصل وعدم توصل
"""
from __future__ import annotations

import gc
import logging
import os
import sys
import threading
from datetime import datetime
from tkinter import filedialog, messagebox
import tkinter as tk

# ── مسار STC_System ──────────────────────────────────────────────────────────
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
STC_DIR  = os.path.normpath(os.path.join(THIS_DIR, "..", "STC_System"))
OUT_DIR  = os.path.normpath(os.path.join(THIS_DIR, "..", "output"))

if STC_DIR not in sys.path:
    sys.path.insert(0, STC_DIR)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO)
_log = logging.getLogger("MaharaSistem")

# ═══════════════════════════════════════════════════════════
#  الثوابت والألوان
# ═══════════════════════════════════════════════════════════
BG          = "#0d1117"
BG_CARD     = "#161b22"
BG_HOVER    = "#1c2333"
BG_INPUT    = "#21262d"
BORDER      = "#30363d"
TXT         = "#f0f6fc"
TXT_MUTED   = "#8b949e"
GREEN       = "#238636"
RED         = "#da3633"
ORANGE      = "#d29922"
BLUE        = "#1f6feb"
PURPLE      = "#8957e5"

FNT_TITLE   = ("Segoe UI", 20, "bold")
FNT_HEAD    = ("Segoe UI", 13, "bold")
FNT_BODY    = ("Segoe UI", 10)
FNT_SMALL   = ("Segoe UI", 9)
FNT_MONO    = ("Consolas", 9)

# ── تعريف الوحدات الأربعة ────────────────────────────────────────────────────
MODULES = [
    {
        "id":    3,
        "key":   "neglect",
        "name":  "الإهمال",
        "icon":  "⏰",
        "color": ORANGE,
        "desc":  "تحليل حالات الإهمال وتصنيف العملاء بناءً على أيام المتابعة",
        "files": [
            {"key": "portfolio", "label": "المحفظة الرئيسية", "required": True},
        ],
    },
    {
        "id":    1,
        "key":   "errors",
        "name":  "أخطاء النظام",
        "icon":  "🔴",
        "color": RED,
        "desc":  "كشف وتصحيح الأخطاء في بيانات المحفظة وتوثيق السداد",
        "files": [
            {"key": "portfolio", "label": "المحفظة الرئيسية",  "required": True},
            {"key": "promise",   "label": "وعود السداد",        "required": False},
        ],
    },
    {
        "id":    7,
        "key":   "targets",
        "name":  "عملاء مستهدفة",
        "icon":  "🎯",
        "color": PURPLE,
        "desc":  "تحديد العملاء ذوي الأولوية وتحليل المديونيات المستهدفة",
        "files": [
            {"key": "portfolio", "label": "المحفظة الرئيسية", "required": True},
        ],
    },
    {
        "id":    2,
        "key":   "contact",
        "name":  "توصل وعدم توصل",
        "icon":  "📞",
        "color": GREEN,
        "desc":  "تصنيف العملاء حسب حالة التواصل وتتبع محاولات الاتصال",
        "files": [
            {"key": "portfolio", "label": "المحفظة الرئيسية", "required": True},
        ],
    },
    {
        "id":    6,
        "key":   "rotation",
        "name":  "السحب والتدوير",
        "icon":  "🔄",
        "color": BLUE,
        "desc":  "سحب جميع عملاء محصل وإعادة توزيعهم على محصلي المشرف بالتساوي",
        "files": [
            {"key": "portfolio", "label": "المحفظة الرئيسية", "required": True},
        ],
    },
]


# ═══════════════════════════════════════════════════════════
#  التطبيق الرئيسي
# ═══════════════════════════════════════════════════════════
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("مهاره سيستم")
        self.root.configure(bg=BG)
        self.root.minsize(950, 650)
        self._center(1100, 720)

        self._panel: tk.Widget | None = None
        self._mod: dict | None = None
        self._paths: dict[str, str] = {}

        self._build_header()
        self._content = tk.Frame(self.root, bg=BG)
        self._content.pack(fill="both", expand=True)
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)

        self._show_welcome()

    # ── Header ───────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self.root, bg="#010409", height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        hdr.columnconfigure(1, weight=1)

        tk.Label(hdr, text="🏢  مهاره سيستم",
                 font=("Segoe UI", 13, "bold"), bg="#010409", fg=BLUE,
                 padx=20).pack(side="left", pady=12)

        self._bread = tk.StringVar(value="الرئيسية")
        tk.Label(hdr, textvariable=self._bread,
                 font=FNT_SMALL, bg="#010409", fg=TXT_MUTED).pack(side="left")

        self._clock_var = tk.StringVar()
        tk.Label(hdr, textvariable=self._clock_var,
                 font=FNT_SMALL, bg="#010409", fg=TXT_MUTED,
                 padx=16).pack(side="right")
        self._tick()

    def _tick(self):
        self._clock_var.set(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        self.root.after(1000, self._tick)

    def _center(self, w, h):
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Panel switcher ────────────────────────────────────────────────────────
    def _show(self, widget: tk.Widget):
        if self._panel:
            self._panel.destroy()
        self._panel = widget
        widget.pack(fill="both", expand=True)

    # ════════════════════════════════════════════════════════
    #  شاشة الاختيار (Welcome)
    # ════════════════════════════════════════════════════════
    def _show_welcome(self):
        self._bread.set("الرئيسية")
        frame = tk.Frame(self._content, bg=BG)

        # العنوان
        tk.Label(frame, text="اختر البرنامج",
                 font=("Segoe UI", 24, "bold"), bg=BG, fg=TXT,
                 pady=30).pack()
        tk.Label(frame, text="اختر أحد الأنظمة لرفع الملفات وبدء التحليل",
                 font=FNT_BODY, bg=BG, fg=TXT_MUTED).pack(pady=(0, 30))

        # شبكة البطاقات 2×2
        grid = tk.Frame(frame, bg=BG)
        grid.pack(padx=60)

        for i, mod in enumerate(MODULES):
            r, c = divmod(i, 2)
            self._make_card(grid, mod, r, c)

        self._show(frame)

    def _make_card(self, parent, mod, row, col):
        card = tk.Frame(parent, bg=BG_CARD, relief="flat",
                        width=380, height=160, cursor="hand2")
        card.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
        card.grid_propagate(False)
        card.columnconfigure(0, weight=1)

        # خط لوني في الأعلى
        bar = tk.Frame(card, bg=mod["color"], height=4)
        bar.pack(fill="x")

        inner = tk.Frame(card, bg=BG_CARD, padx=20, pady=14)
        inner.pack(fill="both", expand=True)

        # أيقونة + اسم
        tk.Label(inner, text=f"{mod['icon']}  {mod['name']}",
                 font=FNT_HEAD, bg=BG_CARD, fg=mod["color"],
                 anchor="e").pack(fill="x")

        tk.Label(inner, text=mod["desc"],
                 font=FNT_SMALL, bg=BG_CARD, fg=TXT_MUTED,
                 wraplength=320, justify="right", anchor="e").pack(fill="x", pady=(6, 0))

        # الملفات المطلوبة
        files_txt = "  |  ".join(
            f['label'] + (" *" if f['required'] else "") for f in mod["files"]
        )
        tk.Label(inner, text=f"الملفات: {files_txt}",
                 font=FNT_SMALL, bg=BG_CARD, fg=TXT_MUTED,
                 anchor="e").pack(fill="x", pady=(8, 0))

        # Hover + click
        def on_enter(e, c=card, b=bar, m=mod):
            c.configure(bg=BG_HOVER)
            b.configure(bg=m["color"])
            for w in c.winfo_children():
                _set_bg(w, BG_HOVER)

        def on_leave(e, c=card, b=bar, m=mod):
            c.configure(bg=BG_CARD)
            b.configure(bg=m["color"])
            for w in c.winfo_children():
                _set_bg(w, BG_CARD)

        def on_click(e, m=mod):
            self._show_upload(m)

        for w in [card, inner] + list(inner.winfo_children()):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

    # ════════════════════════════════════════════════════════
    #  شاشة رفع الملفات (Upload)
    # ════════════════════════════════════════════════════════
    def _show_upload(self, mod: dict):
        self._mod = mod
        self._bread.set(f"الرئيسية  ▶  {mod['name']}")
        frame = tk.Frame(self._content, bg=BG)

        # العنوان
        hdr = tk.Frame(frame, bg=BG, pady=20)
        hdr.pack(fill="x", padx=50)
        tk.Label(hdr, text=f"{mod['icon']}  {mod['name']}",
                 font=("Tahoma", 18, "bold"), bg=BG, fg=mod["color"]).pack(anchor="e")
        tk.Label(hdr, text="اختر الملفات المطلوبة ثم اضغط «تشغيل»",
                 font=FNT_BODY, bg=BG, fg=TXT_MUTED).pack(anchor="e")
        tk.Frame(frame, bg=BORDER, height=1).pack(fill="x", padx=50, pady=(0, 20))

        # منطقة الملفات
        self._file_vars: dict[str, tk.StringVar] = {}
        file_frame = tk.Frame(frame, bg=BG)
        file_frame.pack(padx=80, fill="x")

        for fspec in mod["files"]:
            key   = fspec["key"]
            label = fspec["label"] + (" *" if fspec["required"] else " (اختياري)")
            var   = tk.StringVar(value="لم يتم الاختيار بعد")
            self._file_vars[key] = var

            row = tk.Frame(file_frame, bg=BG, pady=8)
            row.pack(fill="x")
            row.columnconfigure(1, weight=1)

            tk.Label(row, text=label, font=FNT_BODY, bg=BG, fg=TXT,
                     width=22, anchor="e").grid(row=0, column=0, sticky="e", padx=(0, 12))

            entry = tk.Entry(row, textvariable=var, font=FNT_SMALL,
                             bg=BG_INPUT, fg=TXT_MUTED, relief="flat",
                             state="readonly", readonlybackground=BG_INPUT)
            entry.grid(row=0, column=1, sticky="ew", ipady=6)

            tk.Button(row, text="اختيار ملف",
                      font=FNT_SMALL, bg=BLUE, fg=TXT,
                      relief="flat", padx=14, pady=5, cursor="hand2",
                      command=lambda k=key, v=var: self._browse(k, v)
                      ).grid(row=0, column=2, padx=(10, 0))

        # إضافة حقول المشرف والمحصل في حالة السحب والتدوير
        if mod["key"] == "rotation":
            from tkinter import ttk
            
            # صف المشرف
            row_sup = tk.Frame(file_frame, bg=BG, pady=8)
            row_sup.pack(fill="x")
            row_sup.columnconfigure(1, weight=1)
            
            tk.Label(row_sup, text="اسم المشرف : *", font=FNT_BODY, bg=BG, fg=TXT,
                     width=22, anchor="e").grid(row=0, column=0, sticky="e", padx=(0, 12))
            
            self._sup_var = tk.StringVar()
            self._sup_combo = ttk.Combobox(row_sup, textvariable=self._sup_var, state="disabled", font=FNT_SMALL)
            self._sup_combo.grid(row=0, column=1, sticky="ew", ipady=4)
            
            # صف المحصل
            row_col = tk.Frame(file_frame, bg=BG, pady=8)
            row_col.pack(fill="x")
            row_col.columnconfigure(1, weight=1)
            
            tk.Label(row_col, text="المحصل المسحوب : *", font=FNT_BODY, bg=BG, fg=TXT,
                     width=22, anchor="e").grid(row=0, column=0, sticky="e", padx=(0, 12))
            
            self._col_var = tk.StringVar()
            self._col_combo = ttk.Combobox(row_col, textvariable=self._col_var, state="disabled", font=FNT_SMALL)
            self._col_combo.grid(row=0, column=1, sticky="ew", ipady=4)
            
            def on_sup_changed(event):
                sup = self._sup_var.get()
                if sup and hasattr(self, "_rotation_df"):
                    from modules.module6b_rotation import PortfolioRotationModule
                    cols = PortfolioRotationModule.get_collectors_for_supervisor(self._rotation_df, sup)
                    self._col_combo.configure(state="readonly", values=cols)
                    self._col_var.set("")
            
            self._sup_combo.bind("<<ComboboxSelected>>", on_sup_changed)

        # أزرار
        btn_row = tk.Frame(frame, bg=BG, pady=30)
        btn_row.pack()

        tk.Button(btn_row, text="◀  رجوع",
                  font=FNT_BODY, bg=BG_INPUT, fg=TXT_MUTED,
                  relief="flat", padx=20, pady=8, cursor="hand2",
                  command=self._show_welcome).pack(side="left", padx=10)

        tk.Button(btn_row, text="تشغيل  ▶",
                  font=("Segoe UI", 12, "bold"),
                  bg=mod["color"], fg="#fff",
                  relief="flat", padx=28, pady=8, cursor="hand2",
                  command=self._on_run).pack(side="left", padx=10)

        self._show(frame)

    def _browse(self, key: str, var: tk.StringVar):
        global _LAST_DIR
        path = filedialog.askopenfilename(
            title="اختر ملف Excel",
            initialdir=globals().get("_LAST_DIR", os.path.expanduser("~")),
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        if path:
            globals()["_LAST_DIR"] = os.path.dirname(path)
            var.set(path)
            
            if self._mod["key"] == "rotation" and key == "portfolio":
                self._load_rotation_options_desktop(path)

    def _load_rotation_options_desktop(self, path: str):
        try:
            import polars as pl
            from python_calamine import CalamineWorkbook
            wb = CalamineWorkbook.from_path(path)
            sheet = wb.get_sheet_by_name(wb.sheet_names[0])
            data = sheet.to_python()
            if not data:
                self._rotation_df = pl.DataFrame()
            else:
                headers = []
                seen = {}
                for i, h in enumerate(data[0]):
                    h_str = str(h).strip() if h is not None else f"Column_{i}"
                    if not h_str:
                        h_str = f"Column_{i}"
                    if h_str in seen:
                        seen[h_str] += 1
                        h_str = f"{h_str}_{seen[h_str]}"
                    else:
                        seen[h_str] = 0
                    headers.append(h_str)
                records = data[1:]
                self._rotation_df = pl.DataFrame(records, schema=headers, orient="row")
            sups = PortfolioRotationModule.get_supervisors(self._rotation_df)
            self._sup_combo.configure(state="readonly", values=sups)
            self._sup_var.set("")
            self._col_var.set("")
            self._col_combo.configure(state="disabled", values=[])
            messagebox.showinfo("تم قراءة الملف", "تم تحميل قائمة المشرفين بنجاح. يرجى اختيار المشرف والمحصل المسحوب.")
        except Exception as e:
            messagebox.showerror("خطأ في قراءة الملف", f"تعذر قراءة المحفظة:\n{e}")

    def _on_run(self):
        if not self._mod:
            return
        # التحقق من الملفات المطلوبة
        for fspec in self._mod["files"]:
            if fspec["required"]:
                v = self._file_vars.get(fspec["key"], tk.StringVar()).get()
                if not v or v == "لم يتم الاختيار بعد" or not os.path.exists(v):
                    messagebox.showwarning("ملف مطلوب",
                                           f"الرجاء اختيار ملف: {fspec['label']}")
                    return
        
        # معطيات السحب والتدوير
        if self._mod["key"] == "rotation":
            sup = self._sup_var.get()
            col = self._col_var.get()
            if not sup or not col:
                messagebox.showwarning("معطيات ناقصة", "الرجاء اختيار المشرف والمحصل المسحوب أولاً")
                return
            self._rotation_params = {"supervisor": sup, "collector": col}

        # جمع المسارات
        paths = {k: v.get() for k, v in self._file_vars.items()
                 if v.get() and v.get() != "لم يتم الاختيار بعد" and os.path.exists(v.get())}
        self._paths = paths
        self._show_processing()

    # ════════════════════════════════════════════════════════
    #  شاشة المعالجة (Processing)
    # ════════════════════════════════════════════════════════
    def _show_processing(self):
        mod = self._mod
        self._bread.set(f"الرئيسية  ▶  {mod['name']}  ▶  جاري المعالجة")
        frame = tk.Frame(self._content, bg=BG)

        tk.Label(frame, text="⚙️  جاري التحليل...",
                 font=("Segoe UI", 18, "bold"), bg=BG, fg=TXT,
                 pady=30).pack()
        tk.Label(frame, text=mod["name"],
                 font=FNT_BODY, bg=BG, fg=mod["color"]).pack()

        # شريط التقدم
        prog_frame = tk.Frame(frame, bg=BG, pady=20)
        prog_frame.pack()
        self._prog_bar = tk.Label(prog_frame, bg=BG_CARD, width=50, height=2)
        self._prog_bar.pack()
        self._prog_fill = tk.Label(prog_frame, bg=mod["color"], width=0, height=2)
        self._prog_fill.place(in_=self._prog_bar, x=0, y=0, relheight=1)

        # سجل الأحداث
        log_frame = tk.Frame(frame, bg=BG_CARD, padx=10, pady=10)
        log_frame.pack(fill="both", expand=True, padx=60, pady=10)

        self._log_text = tk.Text(log_frame, bg=BG_CARD, fg=TXT,
                                  font=FNT_MONO, relief="flat",
                                  state="disabled", wrap="word",
                                  height=16)
        sb = tk.Scrollbar(log_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="left", fill="y")
        self._log_text.pack(fill="both", expand=True)

        self._log_text.tag_config("STEP",    foreground="#58a6ff")
        self._log_text.tag_config("SUCCESS", foreground="#3fb950")
        self._log_text.tag_config("ERROR",   foreground="#f85149")
        self._log_text.tag_config("INFO",    foreground=TXT_MUTED)

        self._show(frame)

        # تشغيل في خيط خلفي
        threading.Thread(target=self._run_analysis, daemon=True).start()

    def _log(self, msg: str, tag: str = "INFO"):
        def _do():
            self._log_text.configure(state="normal")
            self._log_text.insert("end", msg + "\n", tag)
            self._log_text.see("end")
            self._log_text.configure(state="disabled")
        self.root.after(0, _do)

    def _set_prog(self, pct: float):
        def _do():
            total = self._prog_bar.winfo_width() or 400
            self._prog_fill.place(width=int(total * pct / 100))
        self.root.after(0, _do)

    # ════════════════════════════════════════════════════════
    #  منطق التشغيل
    # ════════════════════════════════════════════════════════
    def _run_analysis(self):
        mod = self._mod
        paths_raw = self._paths

        try:
            from core.data_loader import load_files
            from core.utils import MAIN_PORTFOLIO, PROMISE_PAY, MAHARAH_PAY, COMPANY_PAY
            from export.excel_writer_xl import ExcelReportWriter
            import polars as pl

            # ── 1. قراءة الملفات ─────────────────────────────────────────────
            self._log("📂 قراءة الملفات...", "STEP")
            self._set_prog(10)

            # تعيين مفاتيح المسارات
            path_map: dict[str, str] = {}
            if "portfolio" in paths_raw:
                path_map[MAIN_PORTFOLIO] = paths_raw["portfolio"]
            if "promise" in paths_raw:
                path_map[PROMISE_PAY] = paths_raw["promise"]
            if "maharah" in paths_raw:
                path_map[MAHARAH_PAY] = paths_raw["maharah"]
            if "company" in paths_raw:
                path_map[COMPANY_PAY] = paths_raw["company"]

            dfs, results = load_files(path_map)

            for k, vr in results.items():
                if vr.is_valid:
                    self._log(f"  ✅ {k} — تم التحقق", "SUCCESS")
                else:
                    self._log(f"  ❌ {k} — {vr.summary()}", "ERROR")
                    raise ValueError(f"الملف {k} غير صالح: {vr.summary()}")
            self._set_prog(30)

            portfolio = dfs.get(MAIN_PORTFOLIO)
            promise   = dfs.get(PROMISE_PAY,  pl.DataFrame())
            maharah   = dfs.get(MAHARAH_PAY,  pl.DataFrame())

            # ── 2. تشغيل الوحدة ──────────────────────────────────────────────
            self._log(f"⚙️ تشغيل: {mod['name']}...", "STEP")
            self._set_prog(50)

            os.makedirs(OUT_DIR, exist_ok=True)
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join(OUT_DIR, f"مهاره_{mod['key']}_{ts}.xlsx")
            writer   = ExcelReportWriter(out_path)
            stats    = {}
            task_id  = mod["id"]

            if task_id == 1:
                from modules.module1_errors import SystemErrorsModule
                r = SystemErrorsModule().run(portfolio, promise)
                stats.update(r["stats"])
                writer.write_errors(r["data"])

            elif task_id == 2:
                from modules.module2_contact import ContactStatusModule
                r = ContactStatusModule().run(portfolio)
                stats.update(r["stats"])
                writer.write_contact(r["data"], r["pivot_supervisor"],
                                     r["pivot_collector"], r["pivot_status"])

            elif task_id == 3:
                from modules.module3_neglect import NeglectModule
                r = NeglectModule().run(portfolio)
                stats.update(r["stats"])
                writer.write_neglect(
                    r["data"], r["full_analysis"],
                    r["pivot_summary"], r["pivot_supervisor"],
                    r["pivot_collector"], r["pivot_status"],
                    r["pivot_branch"], r["pivot_portfolio"],
                    r["pivot_days"],
                )

            elif task_id == 7:
                from modules.module7_targets import TargetCustomersModule
                r = TargetCustomersModule().run(portfolio, promise, maharah)
                stats.update(r["stats"])
                writer.write_targets(r["data"], r["pivot_supervisor"])

            elif task_id == 6:
                sup = self._rotation_params["supervisor"]
                col = self._rotation_params["collector"]
                from modules.module6b_rotation import PortfolioRotationModule
                r = PortfolioRotationModule().run(portfolio, col, sup)
                stats.update(r["stats"])
                writer.write_rotation(
                    r["data"],
                    r["execution_report"],
                    r["distribution_summary"],
                    r["withdrawal_summary"],
                )

            self._set_prog(80)
            self._log("📊 إنشاء التقرير...", "STEP")

            writer.write_dashboard(stats, task_id)
            writer.write_summary(stats)
            writer.save()
            self._set_prog(100)

            del dfs, portfolio, promise, maharah
            gc.collect()

            self._log(f"✅ اكتمل! الملف: {os.path.basename(out_path)}", "SUCCESS")
            self.root.after(800, self._show_results, stats, out_path)

        except Exception as exc:
            _log.exception("خطأ")
            self._log(f"❌ خطأ: {exc}", "ERROR")
            self.root.after(0, messagebox.showerror, "خطأ", str(exc))

    # ════════════════════════════════════════════════════════
    #  شاشة النتائج (Results)
    # ════════════════════════════════════════════════════════
    def _show_results(self, stats: dict, out_path: str):
        mod = self._mod
        self._bread.set(f"الرئيسية  ▶  {mod['name']}  ▶  النتائج")
        frame = tk.Frame(self._content, bg=BG)

        tk.Label(frame, text="✅  اكتمل التحليل بنجاح",
                 font=("Segoe UI", 18, "bold"), bg=BG, fg=GREEN,
                 pady=24).pack()
        tk.Label(frame, text=mod["name"],
                 font=FNT_BODY, bg=BG, fg=mod["color"]).pack()

        # إحصائيات
        stats_frame = tk.Frame(frame, bg=BG_CARD, padx=30, pady=20)
        stats_frame.pack(padx=80, pady=20, fill="x")

        tk.Label(stats_frame, text="الإحصائيات",
                 font=FNT_HEAD, bg=BG_CARD, fg=TXT,
                 anchor="e").pack(fill="x", pady=(0, 12))

        for k, v in stats.items():
            row = tk.Frame(stats_frame, bg=BG_CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=str(v), font=("Segoe UI", 12, "bold"),
                     bg=BG_CARD, fg=mod["color"], width=14, anchor="w").pack(side="left")
            tk.Label(row, text=k, font=FNT_BODY, bg=BG_CARD, fg=TXT,
                     anchor="e").pack(side="right")

        # اسم الملف
        tk.Label(frame, text=f"📄  {os.path.basename(out_path)}",
                 font=FNT_BODY, bg=BG, fg=TXT_MUTED, pady=8).pack()

        # أزرار
        btn_row = tk.Frame(frame, bg=BG, pady=16)
        btn_row.pack()

        tk.Button(btn_row, text="📂  فتح مجلد الملف",
                  font=FNT_BODY, bg=BG_INPUT, fg=TXT,
                  relief="flat", padx=18, pady=8, cursor="hand2",
                  command=lambda: os.startfile(os.path.dirname(out_path))
                  ).pack(side="left", padx=8)

        tk.Button(btn_row, text="🔁  تشغيل مجدداً",
                  font=FNT_BODY, bg=mod["color"], fg="#fff",
                  relief="flat", padx=18, pady=8, cursor="hand2",
                  command=lambda: self._show_upload(mod)
                  ).pack(side="left", padx=8)

        tk.Button(btn_row, text="🏠  الرئيسية",
                  font=FNT_BODY, bg=BG_INPUT, fg=TXT_MUTED,
                  relief="flat", padx=18, pady=8, cursor="hand2",
                  command=self._show_welcome
                  ).pack(side="left", padx=8)

        self._show(frame)

    # ── تشغيل ────────────────────────────────────────────────────────────────
    def run(self):
        self.root.mainloop()


# ── مساعد ────────────────────────────────────────────────────────────────────
def _set_bg(widget, color):
    try:
        widget.configure(bg=color)
        for child in widget.winfo_children():
            _set_bg(child, color)
    except Exception:
        pass

_LAST_DIR = os.path.expanduser("~")

# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    App().run()
