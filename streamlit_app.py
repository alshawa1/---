import sys
import os
import tempfile
from datetime import datetime
import polars as pl
import streamlit as st

# ─── إعداد مسار المشروع ───
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
STC_DIR = os.path.join(THIS_DIR, "STC_System")
if STC_DIR not in sys.path:
    sys.path.insert(0, STC_DIR)

from core.data_loader import load_files
from core.utils import MAIN_PORTFOLIO, PROMISE_PAY, MAHARAH_PAY, COMPANY_PAY
from export.excel_writer_xl import ExcelReportWriter

# ─── إعدادات الصفحة والتصميم ───
st.set_page_config(
    page_title="موهبة سيستم - لوحة العمليات الذكية",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تخصيص المظهر بالكامل ودعم اللغة العربية والاتجاه من اليمين لليسار (RTL)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
    
    /* تطبيق خط Cairo والاتجاه */
    html, body, [class*="css"], .stApp {
        font-family: 'Cairo', 'Segoe UI', sans-serif;
        direction: RTL;
        text-align: right;
    }
    
    /* تعديل عناصر واجهة Streamlit لتدعم RTL */
    .stMarkdown, .stSelectbox, .stFileUploader, .stButton, .stMetric {
        direction: RTL;
        text-align: right !important;
    }
    
    div[data-testid="stSidebar"] {
        direction: RTL;
        text-align: right;
    }
    
    /* مظهر وتأثيرات البطاقات والإحصائيات */
    div[data-testid="stMetricValue"] {
        font-family: 'Cairo', sans-serif;
        font-weight: 700;
        font-size: 24px;
        color: #58a6ff !important;
    }
    
    div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
    }
    
    /* تعديل زر التحميل */
    .stDownloadButton button {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%) !important;
        color: white !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 15px rgba(35, 134, 54, 0.3) !important;
        transition: all 0.2s !important;
    }
    .stDownloadButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(35, 134, 54, 0.45) !important;
    }
    </style>
""", unsafe_allow_html=True)

# ─── تعريف البرامج والموديولات ───
MODULES = {
    "rotation": {
        "name": "🔄 السحب والتدوير",
        "desc": "سحب جميع عملاء محصل معين وإعادة توزيعهم بالتساوي على باقي المحصليين التابعين لنفس المشرف، مع الحفاظ على جميع مديونيات العميل الواحد لدى نفس المحصل الجديد.",
        "id": 6,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
        ]
    },
    "contact": {
        "name": "📞 التوصل وعدم التوصل",
        "desc": "تحليل وتصنيف العملاء بناءً على حالات التواصل الرئيسية والفرعية والمتابعة للوصول إلى التصنيف النهائي وتتبع محاولات الاتصال.",
        "id": 2,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
        ]
    },
    "targets": {
        "name": "🎯 العملاء المستهدفة",
        "desc": "تحديد العملاء ذوي الأولوية المرتفعة بناءً على متبقي السداد الموثق ونسب التغطية والتوجيهات المعتمدة.",
        "id": 7,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
        ]
    },
    "neglect": {
        "name": "⏰ الإهمال والمتابعات",
        "desc": "تحليل وتصنيف حالات الإهمال وتحديد العملاء غير المتابعين بناءً على أيام المتابعة وآخر محاولة تواصل.",
        "id": 3,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
        ]
    },
    "errors": {
        "name": "🔴 أخطاء النظام والوعود",
        "desc": "كشف وتوثيق الأخطاء في بيانات المحفظة والمطابقة مع وعود السداد النشطة أو المنتهية لتصحيح حالة العميل.",
        "id": 1,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True},
            {"key": "promise", "label": "ملف وعود السداد (.xlsx) - اختياري", "required": False}
        ]
    },
    "balancing": {
        "name": "⚖️ سحب وتوزيع المحافظ",
        "desc": "إعادة توزيع العملاء من محافظ مصدر على محافظ هدف بخوارزمية ذكية تحقق توازناً مزدوجاً في عدد العملاء وإجمالي متبقي السداد بين جميع المحصلين المستهدفين.",
        "id": 8,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
        ]
    }
}

def read_excel_calamine(file_path: str) -> pl.DataFrame:
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

# ─── مساعد لقراءة المحافظ للبرنامج الجديد ───
@st.cache_data
def scan_portfolio_for_balancing(file_path):
    """يقرأ الملف ويستخرج قائمة المحافظ المتاحة"""
    try:
        df = read_excel_calamine(file_path)
        from modules.module8_balancing import PortfolioBalancingModule
        portfolios = PortfolioBalancingModule.get_portfolios(df)
        collector_map = PortfolioBalancingModule.get_collectors_per_portfolio(df)
        return portfolios, collector_map
    except Exception as e:
        st.error(f"حدث خطأ أثناء فحص الملف: {e}")
        return [], {}

# ─── الدوال المساعدة لتجهيز بيانات التدوير ───
@st.cache_data
def scan_portfolio_for_rotation(file_path):
    """يقرأ ملف المحفظة ويستخرج المشرفين والمحصلين لتسريع عملية الاختيار"""
    try:
        df = read_excel_calamine(file_path)
        from modules.module6b_rotation import PortfolioRotationModule
        supervisors = PortfolioRotationModule.get_supervisors(df)
        mapping = {}
        for sup in supervisors:
            mapping[sup] = PortfolioRotationModule.get_collectors_for_supervisor(df, sup)
        return mapping
    except Exception as e:
        st.error(f"حدث خطأ أثناء فحص الملف: {e}")
        return None

# ─── واجهة المستخدم ───
# الهيدر الرئيسي
st.markdown("<h1 style='text-align: center; color: #58a6ff;'>🏢 مهارة سيستم - لوحة العمليات الذكية</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8b949e; font-size: 16px; margin-bottom: 30px;'>محرك معالجة البيانات المتقدم لأتمتة عمليات مهارة وSTC</p>", unsafe_allow_html=True)

# الشريط الجانبي
with st.sidebar:
    st.markdown("<h3 style='color: #58a6ff; text-align: right;'>⚙️ البرامج المتاحة</h3>", unsafe_allow_html=True)
    selected_key = st.radio(
        label="اختر البرنامج المطلوب تشغيله:",
        options=list(MODULES.keys()),
        format_func=lambda k: MODULES[k]["name"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("<div style='text-align: right; font-size: 12px; color: #8b949e;'>مهارة سيستم &copy; 2026<br>جميع الحقوق محفوظة</div>", unsafe_allow_html=True)

# معلومات البرنامج المختار
module_info = MODULES[selected_key]
st.markdown(f"### {module_info['name']}")
st.info(module_info["desc"])

# قسم رفع الملفات
st.markdown("#### 📂 رفع الملفات المطلوبة")
uploaded_files = {}

cols_upload = st.columns(len(module_info["files"]))
for i, fspec in enumerate(module_info["files"]):
    with cols_upload[i]:
        uploaded_files[fspec["key"]] = st.file_uploader(
            label=fspec["label"],
            type=["xlsx", "xls"],
            key=f"{selected_key}_{fspec['key']}"
        )

# معطيات خاصة ببرنامج السحب والتدوير
rotation_params = {}
if selected_key == "rotation" and uploaded_files.get("portfolio"):
    portfolio_file = uploaded_files["portfolio"]
    
    # حفظ المحفظة مؤقتاً لقراءتها
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_scan:
        tmp_scan.write(portfolio_file.getbuffer())
        tmp_scan_path = tmp_scan.name
    
    try:
        # استخراج خيارات المشرفين والمحصلين
        mapping = scan_portfolio_for_rotation(tmp_scan_path)
        if mapping:
            st.markdown("#### 🔄 إعدادات السحب وإعادة التوزيع")
            c1, c2 = st.columns(2)
            
            with c1:
                selected_sup = st.selectbox(
                    "1. اختر اسم المشرف المسؤول:",
                    options=["-- اختر المشرف --"] + sorted(list(mapping.keys()))
                )
                
            with c2:
                if selected_sup and selected_sup != "-- اختر المشرف --":
                    collectors = sorted(mapping[selected_sup])
                    selected_col = st.selectbox(
                        "2. اسم المحصل المطلوب سحب محفظته:",
                        options=["-- اختر المحصل --"] + collectors
                    )
                else:
                    st.selectbox("2. اسم المحصل المطلوب سحب محفظته:", ["-- اختر المشرف أولاً --"], disabled=True)
                    selected_col = None
            
            # معاينة النتيجة
            if selected_sup and selected_sup != "-- اختر المشرف --" and selected_col and selected_col != "-- اختر المحصل --":
                pool = [c for c in mapping[selected_sup] if c != selected_col]
                if len(pool) == 0:
                    st.error(f"⚠️ لا يوجد محصلون آخرون تحت إشراف '{selected_sup}' لتوزيع المحفظة عليهم!")
                else:
                    st.success(f"✅ سيتم سحب عملاء المحصل **'{selected_col}'** وتوزيعهم بالتساوي على **{len(pool)} محصلين** تحت إشراف المشرف **'{selected_sup}'**.")
                    rotation_params["supervisor"] = selected_sup
                    rotation_params["collector"] = selected_col
    finally:
        try:
            os.unlink(tmp_scan_path)
        except:
            pass

# زر التشغيل
st.markdown("---")
ready_to_run = True

# التحقق من الملفات المطلوبة
for fspec in module_info["files"]:
    if fspec["required"] and not uploaded_files.get(fspec["key"]):
        ready_to_run = False

if selected_key == "rotation" and not rotation_params:
    ready_to_run = False

# ─── واجهة برنامج سحب وتوزيع المحافظ ───────────────────────────────────────
balancing_params = {}
source_ports: list = []
target_ports: list = []
if selected_key == "balancing" and uploaded_files.get("portfolio"):
    portfolio_file = uploaded_files["portfolio"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_scan:
        tmp_scan.write(portfolio_file.getbuffer())
        tmp_scan_path = tmp_scan.name

    try:
        portfolios, collector_map = scan_portfolio_for_balancing(tmp_scan_path)

        if portfolios:
            st.markdown("#### ⚖️ تحديد المحافظ")
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("المحافظ المصدر (السحب منها):")
                source_ports = st.multiselect(
                    label="اختر محفظة أو أكثر لسحب عملائها:",
                    options=portfolios,
                    key="bal_source",
                    label_visibility="collapsed"
                )
                if source_ports:
                    total_source_col = sum(len(collector_map.get(p, [])) for p in source_ports)
                    source_customers = sum(
                        len(set(collector_map.get(p, []))) for p in source_ports
                    )
                    st.info(f"👥 عدد المحصلين في المحافظ المصدر: **{total_source_col}**")

            with c2:
                st.markdown("المحافظ الهدف (التوزيع عليها):")
                available_targets = [p for p in portfolios if p not in (source_ports or [])]
                target_ports = st.multiselect(
                    label="اختر محفظة أو أكثر للتوزيع عليها:",
                    options=available_targets,
                    key="bal_target",
                    label_visibility="collapsed"
                )
                if target_ports:
                    total_target_col = sum(len(collector_map.get(p, [])) for p in target_ports)
                    st.info(f"👥 عدد المحصلين في المحافظ الهدف: **{total_target_col}**")

            # معاينة التحقق
            if source_ports and target_ports:
                overlap = set(source_ports) & set(target_ports)
                if overlap:
                    st.error(f"⚠️ لا يمكن أن تكون المحفظة مصدراً وهدفاً في نفس الوقت: {', '.join(overlap)}")
                else:
                    st.success(
                        f"✅ سيتم سحب عملاء **{' | '.join(source_ports)}** "
                        f"وتوزيعهم بتوازن ذكي على محصلي **{' | '.join(target_ports)}**."
                    )
                    st.markdown("##### ⚙️ إعدادات التوزيع المتقدمة")
                    min_chunk = st.number_input(
                        "الحد الأدنى لعدد العملاء (للتحكم في الرينج، مثلاً 200 يجعل الرينج 200-250)",
                        min_value=50, max_value=1000, value=200, step=10
                    )
                    balancing_params["source"] = source_ports
                    balancing_params["target"] = target_ports
                    balancing_params["chunk"] = min_chunk
    finally:
        try:
            os.unlink(tmp_scan_path)
        except:
            pass

if selected_key == "balancing" and not balancing_params:
    ready_to_run = False

if st.button("🚀 تشغيل التحليل والمعالجة", disabled=not ready_to_run, use_container_width=True):
    temp_files = []
    path_map = {}
    
    try:
        with st.spinner("⏳ جاري قراءة وتجهيز الملفات..."):
            # حفظ الملفات المرفوعة مؤقتاً
            for key, file_obj in uploaded_files.items():
                if file_obj:
                    suffix = os.path.splitext(file_obj.name)[1] or ".xlsx"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(file_obj.getbuffer())
                        tmp_path = tmp.name
                        temp_files.append(tmp_path)
                        
                        if key == "portfolio":
                            path_map[MAIN_PORTFOLIO] = tmp_path
                        elif key == "promise":
                            path_map[PROMISE_PAY] = tmp_path
            
            # 1. قراءة الملفات
            dfs, results = load_files(path_map)
            
            for k, vr in results.items():
                if not vr.is_valid:
                    st.error(f"❌ الملف {k} غير صالح: {vr.summary()}")
                    st.stop()
            
            portfolio = dfs.get(MAIN_PORTFOLIO)
            promise = dfs.get(PROMISE_PAY, pl.DataFrame())
            
        with st.spinner("⚙️ جاري معالجة البيانات وتطبيق القواعد الحسابية..."):
            # 2. تشغيل الموديول المناسب
            task_id = module_info["id"]
            stats = {}
            
            # تجهيز ملف المخرجات المؤقت
            out_fd, out_path = tempfile.mkstemp(suffix=".xlsx")
            os.close(out_fd)
            temp_files.append(out_path)
            
            writer = ExcelReportWriter(out_path)
            
            if task_id == 1:
                from modules.module1_errors import SystemErrorsModule
                r = SystemErrorsModule().run(portfolio, promise)
                stats.update(r["stats"])
                writer.write_errors(r["data"])
                
            elif task_id == 2:
                from modules.module2_contact import ContactStatusModule
                r = ContactStatusModule().run(portfolio)
                stats.update(r["stats"])
                writer.write_contact(
                    r["data"], r["pivot_supervisor"],
                    r["pivot_collector"], r["pivot_status"]
                )
                
            elif task_id == 3:
                from modules.module3_neglect import NeglectModule
                r = NeglectModule().run(portfolio)
                stats.update(r["stats"])
                writer.write_neglect(
                    r["data"], r["full_analysis"],
                    r["pivot_summary"], r["pivot_supervisor"],
                    r["pivot_collector"], r["pivot_status"],
                    r["pivot_branch"], r["pivot_portfolio"],
                    r["pivot_days"]
                )
                
            elif task_id == 7:
                from modules.module7_targets import TargetCustomersModule
                r = TargetCustomersModule().run(portfolio, promise, pl.DataFrame())
                stats.update(r["stats"])
                writer.write_targets(r["data"], r["pivot_supervisor"])
                
            elif task_id == 6:
                sup = rotation_params["supervisor"]
                col = rotation_params["collector"]
                from modules.module6b_rotation import PortfolioRotationModule
                r = PortfolioRotationModule().run(portfolio, col, sup)
                stats.update(r["stats"])
                writer.write_rotation(
                    r["data"],
                    r["execution_report"],
                    r["distribution_summary"],
                    r["withdrawal_summary"]
                )

            elif task_id == 8:
                from modules.module8_balancing import PortfolioBalancingModule
                tgt = balancing_params.get("target") or None
                r = PortfolioBalancingModule().run(
                    portfolio,
                    source_portfolios=balancing_params["source"],
                    target_portfolios=tgt,
                    min_receiver_chunk=balancing_params.get("chunk", 200)
                )
                stats.update(r["stats"])
                writer.write_balancing(
                    r["data"],
                    r["summary_pivot"],
                    r.get("planning_sheet"),
                    r.get("source_summary"),
                    r.get("final_result_sheet"),
                )
            
            writer.write_dashboard(stats, task_id)
            writer.write_summary(stats)
            writer.save()
            
        st.balloons()
        st.success("✨ اكتملت معالجة البيانات بنجاح وتم إنشاء التقرير المنسق!")
        
        # 3. عرض الإحصائيات
        st.markdown("#### 📊 ملخص نتائج التقرير")
        stats_cols = st.columns(min(len(stats), 4))
        for j, (k, v) in enumerate(stats.items()):
            col_idx = j % len(stats_cols)
            with stats_cols[col_idx]:
                st.metric(label=k, value=str(v))
        
        # عرض جدول التوازن النهائي للمحصلين (تم تعديل أسماء الأعمدة لتطابق المخرجات الفعلية)
        if task_id == 8 and 'r' in locals() and "summary_pivot" in r:
            st.markdown("---")
            st.markdown("#### 📋 جدول ملخص التوزيع النهائي للمحصلين")
            show_df = r["summary_pivot"].select(["المحصل", "اليوزر", "عدد العملاء بعد", "إجمالي متبقي السداد"])
            
            # استبعاد صفوف المؤشرات الإحصائية من العرض المباشر بأمان وحمايتها من الـ Nulls
            show_df = show_df.filter(~pl.col("المحصل").str.contains("📉|📈").fill_null(False))
            st.dataframe(show_df.to_pandas(), use_container_width=True, hide_index=True)
        
        # 4. زر تحميل التقرير
        with open(out_path, "rb") as f_out:
            excel_bytes = f_out.read()
            
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_name = f"مهاره_{selected_key}_{ts_str}.xlsx"
        
        st.markdown("---")
        st.download_button(
            label="📥 تحميل التقرير النهائي (Excel Mapped & Styled)",
            data=excel_bytes,
            file_name=download_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    except Exception as e:
        st.exception(e)
        st.error(f"❌ حدث خطأ أثناء تشغيل النظام: {e}")
        
    finally:
        # تنظيف الملفات المؤقتة
        for p in temp_files:
            try:
                os.unlink(p)
            except:
                pass
