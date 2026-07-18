# -*- coding: utf-8 -*-
"""
برنامج تشغيل توازن المحافظ الشامل (Portfolio Balancing Runner)
يقوم بتشغيل خوارزمية التوازن وحفظ النتائج في ملف Excel منسق بالكامل.
"""
import os
import sys
import time

# ترميز الإخراج على ويندوز
sys.stdout.reconfigure(encoding='utf-8')

# إضافة مجلد النظام للمسارات
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'STC_System'))

try:
    import polars as pl
    from core.data_loader import load_files
    from core.utils import MAIN_PORTFOLIO
    from modules.module8_balancing import PortfolioBalancingModule, _detect
    from export.excel_writer_xl import ExcelReportWriter
except ImportError as e:
    print(f"❌ خطأ في تحميل موديولات النظام: {e}")
    sys.exit(1)

def main():
    print("=" * 60)
    print("      📊 نظام توازن المحافظ الشامل (Snake-Draft Balancing) 📊")
    print("=" * 60)

    # 1. البحث عن ملف المحفظة
    portfolio_file = 'المحفظه الموزعه.xlsx'
    if not os.path.exists(portfolio_file):
        # البحث عن أي ملف إكسل يحتوي على كلمة المحفظة
        excels = [f for f in os.listdir('.') if f.endswith('.xlsx') and not f.startswith('~$') and not f.startswith('تقرير_')]
        if excels:
            portfolio_file = excels[0]
            print(f"⚠️ لم يتم العثور على '{portfolio_file}' الافتراضي، تم استخدام الملف: {portfolio_file}")
        else:
            print("❌ لم يتم العثور على أي ملفات إكسل (.xlsx) في المجلد الحالي!")
            input("\nاضغط Enter للخروج...")
            return

    # 2. تحميل البيانات
    print(f"📂 جاري تحميل ملف المحفظة: {portfolio_file} ...")
    start_time = time.time()
    try:
        dfs, results = load_files({MAIN_PORTFOLIO: portfolio_file})
        df = dfs[MAIN_PORTFOLIO]
        print(f"✅ تم تحميل {len(df):,} صف بنجاح في {time.time() - start_time:.2f} ثانية.")
    except Exception as e:
        print(f"❌ خطأ أثناء تحميل الملف: {e}")
        input("\nاضغط Enter للخروج...")
        return

    # 3. استخراج المحافظ المتاحة
    prt_col = _detect(df, ["المحافظ", "المحفظة", "اسم المحفظة", "Portfolio", "محفظة", "محافظ"])
    if not prt_col:
        print("❌ لم يتم العثور على عمود المحفظة في الملف! تأكد من وجود عمود باسم 'المحافظ' أو 'المحفظة'.")
        input("\nاضغط Enter للخروج...")
        return

    portfolios = (
        df.select(prt_col)
        .unique()
        .to_series()
        .cast(pl.String)
        .str.strip_chars()
        .drop_nulls()
        .sort()
        .to_list()
    )

    if not portfolios:
        print("❌ لا توجد محافظ متاحة في الملف.")
        input("\nاضغط Enter للخروج...")
        return

    print("\nالمحافظ المتاحة في الملف:")
    for i, p in enumerate(portfolios, 1):
        count_rows = len(df.filter(pl.col(prt_col).cast(pl.String).str.strip_chars() == p))
        print(f"  [{i}] {p} ({count_rows:,} صف)")

    # 4. اختيار المحفظة المصدر
    print("\n" + "-" * 50)
    print("الرجاء اختيار رقم المحفظة المصدر (التي تريد السحب منها للموازنة):")
    print("مثال: اكتب 1 ثم اضغط Enter")
    print("-" * 50)
    try:
        choice = int(input("أدخل رقم الاختيار: "))
        if choice < 1 or choice > len(portfolios):
            raise ValueError()
        source_p = portfolios[choice - 1]
    except (ValueError, IndexError):
        source_p = portfolios[0]
        print(f"⚠️ اختيار غير صالح. تم استخدام المحفظة الأولى تلقائياً: {source_p}")

    # 4.5. اختيار الحد الأدنى لعدد العملاء لكل مستقبل
    print("\n" + "-" * 50)
    print("الحد الأدنى لعدد العملاء الجدد لكل محصل مستقبل:")
    print("اكتب 100 أو 80 (الافتراضي: 100)")
    print("أو اضغط Enter مباشرة للتوزيع بالتساوي على جميع المحصلين دون حد أدنى")
    print("-" * 50)
    min_chunk_val = None
    try:
        chunk_input = input("الحد الأدنى (الافتراضي 100): ").strip()
        if chunk_input:
            min_chunk_val = int(chunk_input)
            print(f"✅ سيتم توزيع العملاء بحيث لا يقل نصيب أي مستقبل نشط عن {min_chunk_val} عميل.")
        else:
            print("ℹ️ تم اختيار التوزيع الافتراضي بالتساوي على الجميع.")
    except ValueError:
        print("⚠️ إدخال غير صالح. سيتم استخدام التوزيع الافتراضي بالتساوي.")

    print(f"\n🚀 جاري تشغيل موازنة المحافظ (السحب من: '{source_p}')...")
    
    # 5. تشغيل موديول التوازن
    bm = PortfolioBalancingModule()
    try:
        res = bm.run(df, source_portfolios=[source_p], min_receiver_chunk=min_chunk_val)

    except Exception as e:
        import traceback
        print("❌ حدث خطأ أثناء تشغيل موديول التوازن:")
        traceback.print_exc()
        input("\nاضغط Enter للخروج...")
        return

    # 6. كتابة وتصدير ملف التقرير النهائي
    output_file = 'تقرير_توازن_المحافظ.xlsx'
    print(f"\n💾 جاري حفظ وتصدير ملف التقرير المنسق: {output_file} ...")
    try:
        writer = ExcelReportWriter(output_file)
        writer.write_balancing(
            data=res["data"],
            summary_pivot=res["summary_pivot"],
            planning_sheet=res["planning_sheet"],
            source_summary=res.get("source_summary")
        )
        writer.save()
        print(f"✅ تم تصدير وحفظ التقرير بنجاح في: {os.path.abspath(output_file)}")
    except Exception as e:
        import traceback
        print(f"❌ خطأ أثناء حفظ ملف الإكسل: {e}")
        traceback.print_exc()
        input("\nاضغط Enter للخروج...")
        return

    # 7. عرض الإحصاءات الملخصة
    print("\n" + "=" * 60)
    print("   📊 ملخص نتائج الموازنة والتوزيع 📊")
    print("=" * 60)
    for k, v in res["stats"].items():
        print(f"  • {k}: {v}")
    
    print("\n" + "=" * 60)
    print("🎉 تم التوازن وتوليد الشيتات بنجاح!")
    print("الشيتات التي تم إنشاؤها:")
    print("  1. 'بيانات المحفظة' — الملف الكامل مضافاً إليه الأعمدة الجديدة ('النهائي'، 'المحصل الجديد'، 'حالة السحب'، 'اليوزر').")
    print("  2. 'ملخص التوزيع' — حالة أعداد وأرصدة جميع المحصلين بعد التوازن بنظام Snake-Draft.")
    print("  3. 'ملخص المحفظة المصدر' — يوضح كل محصل سُحب منه، عدد عملائه وأرصادهم قبل وبعد، وحالة السحب والتوزيع بالتفصيل.")
    print("  4. 'خطة التوازن' — كشف تفصيلي شامل لحالة كل محصل قبل وبعد وعمليات السحب والإضافة.")
    print("=" * 60)

    input("\nاضغط Enter للإغلاق...")

if __name__ == "__main__":
    main()
