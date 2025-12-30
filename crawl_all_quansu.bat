@echo off
chcp 65001 >nul
title Military News Crawler - All Sources

echo ========================================
echo Starting 4 Military News Crawlers
echo ========================================
echo.
echo [1] VNExpress - the-gioi/quan-su
echo [2] DanTri    - the-gioi/quan-su
echo [3] VietnamNet- the-gioi/quan-su
echo [4] QDND      - quoc-te/quan-su-the-gioi
echo.
echo Press Ctrl+C in any window to stop
echo ========================================
echo.

timeout /t 2 >nul

start "VNExpress Crawler" cmd /k python VNNewsCrawler.py --config config_vnexpress_quansu.yml --continuous

timeout /t 1 >nul

start "DanTri Crawler" cmd /k python VNNewsCrawler.py --config config_dantri_quansu.yml --continuous

timeout /t 1 >nul

start "VietnamNet Crawler" cmd /k python VNNewsCrawler.py --config config_vietnamnet_quansu.yml --continuous

timeout /t 1 >nul

start "QDND Crawler" cmd /k python VNNewsCrawler.py --config config_qdnd_quansu.yml --continuous

echo.
echo ========================================
echo All crawlers started!
echo Check the 4 windows for progress
echo ========================================
echo.
pause