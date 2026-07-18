@echo off
chcp 65001 > nul
title تشغيل واجهة مهاره سيستم (الموقع)

echo.
echo  ======================================================
echo      جاري تشغيل واجهة الموقع (مهاره سيستم)
echo  ======================================================
echo.

REM تثبيت flask لو مش موجود
C:\Users\dell\anaconda3\python.exe -c "import flask" 2>nul || (
    echo  [جاري تثبيت المكتبة اللازمة Flask...]
    C:\Users\dell\anaconda3\python.exe -m pip install flask -q
)

echo  [*] السيرفر شغّال ومتاح على: http://127.0.0.1:5050
echo  [*] سيتم فتح المتصفح تلقائياً خلال ثانية واحدة...
echo  [*] لإيقاف التشغيل، أغلق هذه النافذة السوداء.
echo.

C:\Users\dell\anaconda3\python.exe "%~dp0server.py"
pause
