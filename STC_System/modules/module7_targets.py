"""
modules/module7_targets.py
──────────────────────────
Module 7 — العملاء المستهدفة (Target Customers) using Polars.
Works only on the main portfolio file (المحفظة الموزعة).
Classifies customers into "مستهدف" or "غير مستهدف" based on positive and negative keywords in the follow-up column (المتابعة).
"""
from __future__ import annotations

import logging
from typing import Dict

import polars as pl

_log = logging.getLogger("Module7_Targets")

POSITIVE = "مستهدف"
NEGATIVE = "غير مستهدف"


class TargetCustomersModule:
    CLASS_COL    = "العملاء المستهدفة"
    PRIORITY_COL = "أولوية التحصيل"
    REASON_COL   = "سبب التصنيف"

    def run(
        self,
        portfolio: pl.DataFrame,
        promise: pl.DataFrame = None,
        maharah: pl.DataFrame = None,
    ) -> Dict:
        _log.info("▶ بدء تحديد العملاء المستهدفة (Polars)")

        # 1. إضافة كولوم عدد العملاء = 1 / countif(رقم الهوية)
        id_col = next((c for c in ["رقم الهوية", "الهوية"] if c in portfolio.columns), None)
        if id_col:
            portfolio = portfolio.with_columns(
                (pl.lit(1.0) / pl.col(id_col).count().over(id_col).cast(pl.Float64)).alias("عدد العملاء")
            )
        else:
            portfolio = portfolio.with_columns(pl.lit(1.0).alias("عدد العملاء"))

        df = portfolio.clone()

        # 2. تصنيف العملاء بناءً على كولوم المتابعة
        df = self._classify(df)

        # 3. إعداد الجداول المحورية والإحصائيات
        positive_df = df.filter(pl.col(self.CLASS_COL) == POSITIVE)

        piv_sup = self._build_pivot(df, "المشرف")
        collector = next((c for c in ["المحصل", "الموظف"] if c in df.columns), "")
        piv_col   = self._build_pivot(df, collector) if collector else pl.DataFrame()

        total = len(df)
        pos_count = df.filter(pl.col(self.CLASS_COL) == POSITIVE).height
        neg_count = df.filter(pl.col(self.CLASS_COL) == NEGATIVE).height

        stats = {
            "إجمالي العملاء":    total,
            "مستهدف":            pos_count,
            "غير مستهدف":        neg_count,
            "نسبة المستهدفين %": round(pos_count / total * 100, 1) if total else 0.0,
        }

        return {
            "data":             df,
            "positive_data":    positive_df,
            "pivot_supervisor": piv_sup,
            "pivot_collector":  piv_col,
            "stats":            stats,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _normalize_column(self, df: pl.DataFrame, col_name: str) -> pl.Expr:
        """
        توحيد الحروف والنصوص لتسهيل البحث بالكلمات المفتاحية
        """
        return (
            pl.col(col_name)
            .fill_null("")
            .cast(pl.String)
            .str.strip_chars()
            .str.to_lowercase()
            .str.replace_all("أ", "ا")
            .str.replace_all("إ", "ا")
            .str.replace_all("آ", "ا")
            .str.replace_all("ة", "ه")
            .str.replace_all("ى", "ي")
        )

    def _classify(self, df: pl.DataFrame) -> pl.DataFrame:
        note_col = next((c for c in ["المتابعة", "الملاحظة", "الملاحظات", "ملاحظة"] if c in df.columns), None)

        if not note_col:
            # إذا لم يتم العثور على عمود المتابعة، يتم تصنيف الجميع كغير مستهدف افتراضياً
            _log.warning("لم يتم العثور على عمود المتابعة في ملف المحفظة!")
            return df.with_columns([
                pl.lit(NEGATIVE).alias(self.CLASS_COL),
                pl.lit("لا يوجد عمود متابعة").alias(self.REASON_COL),
                pl.lit(2).cast(pl.Int32).alias(self.PRIORITY_COL),
            ])

        # الكلمات الإيجابية والسلبية للبحث عنها
        POS_KEYWORDS = [
            "اول الشهر", "أول الشهر", "هيدفع", "سيدفع", "يسدد", "سيسدد", 
            "وعد", "سداد", "مواطن", "يوم مواطن", "قسط", "اقساط", "أقساط", 
            "تسوية", "جدولة", "جدوله", "راتب", "الراتب", "دفعة", "دفعه", 
            "اتفاق", "معاش", "بينزل", "ينزل", "بكره", "بكرة", "يسد", "ابشر", 
            "بيسدد", "بسدد", "بسددها"
        ]
        NEG_KEYWORDS = [
            "لايرد", "لا يرد", "مايرد", "مايردش", "ما يرد", "ما ترد", "لم يرد", 
            "مغلق", "خروج نهائي", "متوفي", "وفاة", "بالسجن", "سجن", "مسجون",
            "غير صحيح", "لا يخص", "لايخص", "رقم خطأ", "رقم غلط", "الرقم غير صحيح",
            "الارقام لا تخص", "بريد صوتي", "بريد", "بيزي", "كنسل", "يكنسل", "يفصل",
            "يرد و ما يتكلم", "يرد وساكته", "ردت وساكته", "مرفوض", "رفض", "رافض",
            "رافض السداد", "رفض السداد", "ما يقدر", "ما يقدر يسدد", "مقدر اسدد",
            "ما عندي قدره", "انكر", "تنكر", "مستحيل", "اشتكي"
        ]

        # تنظيف عمود المتابعة
        note_expr = self._normalize_column(df, note_col)

        # فحص الكلمات المفتاحية
        has_pos = pl.lit(False)
        pos_reasons = []
        for kw in POS_KEYWORDS:
            # توحيد الكلمة المفتاحية أيضاً لمطابقة صحيحة
            kw_norm = kw.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
            match_cond = note_expr.str.contains(kw_norm, literal=True)
            has_pos = has_pos | match_cond
            pos_reasons.append(pl.when(match_cond).then(pl.lit(f"كلمة إيجابية: {kw}")).otherwise(pl.lit(None)))

        has_neg = pl.lit(False)
        neg_reasons = []
        for kw in NEG_KEYWORDS:
            kw_norm = kw.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
            match_cond = note_expr.str.contains(kw_norm, literal=True)
            has_neg = has_neg | match_cond
            neg_reasons.append(pl.when(match_cond).then(pl.lit(f"كلمة سلبية: {kw}")).otherwise(pl.lit(None)))

        # دمج الأسباب للمستهدف وغير المستهدف
        pos_reason_expr = pl.coalesce(pos_reasons).fill_null("إيجابي")
        neg_reason_expr = pl.coalesce(neg_reasons).fill_null("سلبي")

        # العميل مستهدف فقط إذا احتوت المتابعة على كلمة إيجابية ولم تحتوي على أي كلمة سلبية
        is_targeted = has_pos & (~has_neg)

        class_expr = pl.when(is_targeted).then(pl.lit(POSITIVE)).otherwise(pl.lit(NEGATIVE))
        reason_expr = pl.when(is_targeted).then(pos_reason_expr).otherwise(
            pl.when(has_neg).then(neg_reason_expr).otherwise(pl.lit("لا توجد مؤشرات إيجابية"))
        )

        df = df.with_columns([
            class_expr.alias(self.CLASS_COL),
            reason_expr.alias(self.REASON_COL),
        ])

        # تعيين أولوية التحصيل: 1 للمستهدفين، 2 لغير المستهدفين
        df = df.with_columns(
            pl.when(pl.col(self.CLASS_COL) == POSITIVE).then(pl.lit(1))
            .otherwise(pl.lit(2))
            .cast(pl.Int32)
            .alias(self.PRIORITY_COL)
        )

        return df

    def _build_pivot(self, df: pl.DataFrame, group_col: str) -> pl.DataFrame:
        if not group_col or group_col not in df.columns:
            return pl.DataFrame()

        try:
            pivot = (
                df.group_by([group_col, self.CLASS_COL])
                .len()
                .pivot(on=self.CLASS_COL, index=group_col, values="len")
                .fill_null(0)
            )
            for col in [POSITIVE, NEGATIVE]:
                if col not in pivot.columns:
                    pivot = pivot.with_columns(pl.lit(0).alias(col))
            pivot = pivot.with_columns(
                (pl.col(POSITIVE) + pl.col(NEGATIVE)).alias("الإجمالي")
            )
            return pivot
        except Exception as e:
            _log.warning("فشل إنشاء محور العملاء المستهدفين لـ %s: %s", group_col, e)
            return pl.DataFrame()
