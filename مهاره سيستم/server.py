"""
مهاره سيستم — Flask Server
يشغّل الواجهة الويب ويقبل الملفات ويشغّل الموديولات مباشرة
"""
from __future__ import annotations

import gc
import io
import logging
import os
import sys
import tempfile
import threading
from datetime import datetime

# ── مسار STC_System ──────────────────────────────────────────────────────────
THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
STC_DIR    = os.path.normpath(os.path.join(THIS_DIR, "..", "STC_System"))
OUTPUT_DIR = os.path.normpath(os.path.join(THIS_DIR, "..", "output"))

if STC_DIR not in sys.path:
    sys.path.insert(0, STC_DIR)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask import Flask, request, jsonify, send_file, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")
logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
_log = logging.getLogger("MaharaServer")

MODULE_CONFIG = {
    "neglect": {
        "title":   "الإهمال",
        "module":  3,
        "files":   [{"key": "portfolio", "label": "المحفظة الرئيسية", "required": True}],
    },
    "errors": {
        "title":   "أخطاء النظام",
        "module":  1,
        "files":   [
            {"key": "portfolio", "label": "المحفظة الرئيسية",  "required": True},
            {"key": "promise",   "label": "وعود السداد",        "required": False},
        ],
    },
    "targets": {
        "title":   "عملاء مستهدفة",
        "module":  7,
        "files":   [
            {"key": "portfolio", "label": "المحفظة الرئيسية",  "required": True},
        ],
    },
    "contact": {
        "title":   "توصل وعدم توصل",
        "module":  2,
        "files":   [{"key": "portfolio", "label": "المحفظة الرئيسية", "required": True}],
    },
    "rotation": {
        "title":   "السحب والتدوير",
        "module":  6,
        "files":   [{"key": "portfolio", "label": "المحفظة الرئيسية", "required": True}],
    },
    "balancing": {
        "title":   "سحب وتوزيع المحافظ",
        "module":  8,
        "files":   [{"key": "portfolio", "label": "المحفظة الرئيسية", "required": True}],
    },
}

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/config/<module_key>")
def get_config(module_key):
    cfg = MODULE_CONFIG.get(module_key)
    if not cfg:
        return jsonify({"error": "وحدة غير موجودة"}), 404
    return jsonify(cfg)

@app.route("/api/rotation/inspect", methods=["POST"])
def inspect_rotation_file():
    import tempfile, polars as pl
    from modules.module6b_rotation import PortfolioRotationModule
    
    file = request.files.get("portfolio")
    if not file or not file.filename:
        return jsonify({"error": "ملف المحفظة مفقود"}), 400
        
    try:
        suffix = os.path.splitext(file.filename)[1] or ".xlsx"
        # delete=False is safer for Windows NamedTemporaryFiles
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_name = tmp.name
        from python_calamine import CalamineWorkbook
        wb = CalamineWorkbook.from_path(tmp_name)
        sheet = wb.get_sheet_by_name(wb.sheet_names[0])
        data = sheet.to_python()
        if not data:
            df = pl.DataFrame()
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
            df = pl.DataFrame(records, schema=headers, orient="row")
        try:
            os.unlink(tmp_name)
        except:
            pass
            
        # Get supervisors and their collectors
        sups = PortfolioRotationModule.get_supervisors(df)
        mapping = {}
        for sup in sups:
            cols = PortfolioRotationModule.get_collectors_for_supervisor(df, sup)
            mapping[sup] = cols
            
        return jsonify({"supervisors": mapping})
    except Exception as e:
        _log.exception("Error inspecting rotation file")
        return jsonify({"error": str(e)}), 500


def _read_calamine_df(file_path: str):
    """Helper: reads an Excel file via python_calamine into a polars DataFrame."""
    import polars as pl
    from python_calamine import CalamineWorkbook
    wb = CalamineWorkbook.from_path(file_path)
    sheet = wb.get_sheet_by_name(wb.sheet_names[0])
    data = sheet.to_python()
    if not data:
        return pl.DataFrame()
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
    return pl.DataFrame(records, schema=headers, orient="row")


@app.route("/api/balancing/inspect", methods=["POST"])
def inspect_balancing_file():
    """يقرأ ملف المحفظة ويعيد قائمة المحافظ المتاحة وعدد المحصلين."""
    from modules.module8_balancing import PortfolioBalancingModule

    file = request.files.get("portfolio")
    if not file or not file.filename:
        return jsonify({"error": "ملف المحفظة مفقود"}), 400

    try:
        suffix = os.path.splitext(file.filename)[1] or ".xlsx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_name = tmp.name

        df = _read_calamine_df(tmp_name)
        try:
            os.unlink(tmp_name)
        except:
            pass

        portfolios = PortfolioBalancingModule.get_portfolios(df)
        collector_map = PortfolioBalancingModule.get_collectors_per_portfolio(df)

        # Summarize: {portfolio: collector_count}
        summary = {p: len(v) for p, v in collector_map.items()}

        return jsonify({"portfolios": portfolios, "collector_counts": summary})
    except Exception as e:
        _log.exception("خطأ فحص ملف التوزيع")
        return jsonify({"error": str(e)}), 500

@app.route("/api/run/<module_key>", methods=["POST"])
def run_module(module_key):
    cfg = MODULE_CONFIG.get(module_key)
    if not cfg:
        return jsonify({"error": "وحدة غير موجودة"}), 404

    import tempfile, polars as pl
    from core.data_loader import load_files
    from core.utils import MAIN_PORTFOLIO, PROMISE_PAY, MAHARAH_PAY, COMPANY_PAY

    temp_paths: dict[str, str] = {}
    tmp_files: list[str] = []

    try:
        for fspec in cfg["files"]:
            key   = fspec["key"]
            label = fspec["label"]
            req   = fspec["required"]
            file  = request.files.get(key)

            if not file and req:
                return jsonify({"error": f"الملف المطلوب مفقود: {label}"}), 400

            if file and file.filename:
                suffix = os.path.splitext(file.filename)[1] or ".xlsx"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                file.save(tmp.name)
                tmp.close()
                tmp_files.append(tmp.name)
                temp_paths[key] = tmp.name

        path_map: dict[str, str] = {}
        if "portfolio" in temp_paths:
            path_map[MAIN_PORTFOLIO] = temp_paths["portfolio"]
        if "promise" in temp_paths:
            path_map[PROMISE_PAY] = temp_paths["promise"]
        if "maharah" in temp_paths:
            path_map[MAHARAH_PAY] = temp_paths["maharah"]

        dfs, results = load_files(path_map)

        for k, vr in results.items():
            if not vr.is_valid:
                return jsonify({"error": f"الملف {k} غير صالح: {vr.summary()}"}), 400

        portfolio = dfs.get(MAIN_PORTFOLIO)
        promise   = dfs.get(PROMISE_PAY,  pl.DataFrame())
        maharah   = dfs.get(MAHARAH_PAY,  pl.DataFrame())

        from export.excel_writer_xl import ExcelReportWriter
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(OUTPUT_DIR, f"مهاره_{module_key}_{ts}.xlsx")
        writer   = ExcelReportWriter(out_path)
        all_stats: dict = {}

        task_id = cfg["module"]

        if task_id == 1:
            from modules.module1_errors import SystemErrorsModule
            r = SystemErrorsModule().run(portfolio, promise)
            all_stats.update(r["stats"])
            writer.write_errors(r["data"])

        elif task_id == 2:
            from modules.module2_contact import ContactStatusModule
            r = ContactStatusModule().run(portfolio)
            all_stats.update(r["stats"])
            writer.write_contact(
                r["data"], r["pivot_supervisor"],
                r["pivot_collector"], r["pivot_status"],
            )

        elif task_id == 3:
            from modules.module3_neglect import NeglectModule
            r = NeglectModule().run(portfolio)
            all_stats.update(r["stats"])
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
            all_stats.update(r["stats"])
            writer.write_targets(r["data"], r["pivot_supervisor"])

        elif task_id == 6:
            sup = request.form.get("supervisor")
            col = request.form.get("collector")
            if not sup or not col:
                return jsonify({"error": "الرجاء تحديد المشرف والمحصل المسحوب"}), 400
                
            from modules.module6b_rotation import PortfolioRotationModule
            r = PortfolioRotationModule().run(portfolio, col, sup)
            all_stats.update(r["stats"])
            writer.write_rotation(
                r["data"],
                r["execution_report"],
                r["distribution_summary"],
                r["withdrawal_summary"],
            )

        elif task_id == 8:
            source_raw = request.form.get("source_portfolios", "")
            target_raw = request.form.get("target_portfolios", "")
            source_list = [s.strip() for s in source_raw.split("|") if s.strip()]
            target_list = [s.strip() for s in target_raw.split("|") if s.strip()]
            if not source_list:
                return jsonify({"error": "الرجاء تحديد المحافظ المصدر"}), 400

            from modules.module8_balancing import PortfolioBalancingModule
            r = PortfolioBalancingModule().run(
                portfolio,
                source_portfolios=source_list,
                target_portfolios=target_list or None,
            )
            all_stats.update(r["stats"])
            writer.write_balancing(
                r["data"],
                r["summary_pivot"],
            )

        writer.write_dashboard(all_stats, task_id)
        writer.write_summary(all_stats)
        writer.save()

        del dfs, portfolio, promise, maharah
        gc.collect()

        return jsonify({
            "ok":      True,
            "stats":   {k: str(v) for k, v in all_stats.items()},
            "file":    os.path.basename(out_path),
            "path":    out_path,
        })

    except Exception as exc:
        _log.exception("خطأ أثناء التشغيل")
        return jsonify({"error": str(exc)}), 500

    finally:
        for p in tmp_files:
            try: os.unlink(p)
            except: pass

@app.route("/api/download/<filename>")
def download_file(filename):
    safe = os.path.basename(filename)
    full = os.path.join(OUTPUT_DIR, safe)
    if not os.path.exists(full):
        return jsonify({"error": "الملف غير موجود"}), 404
    return send_file(full, as_attachment=True, download_name=safe)

if __name__ == "__main__":
    import webbrowser
    threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5050")).start()
    app.run(host="127.0.0.1", port=5050, debug=False)
