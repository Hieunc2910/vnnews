@echo off
echo ========================================
echo Crawling Quan Su from 3 News Sources
echo ========================================
echo.

echo [1/3] Crawling VNExpress Quan Su
python VNNewsCrawler.py --config config_vnexpress_quansu.yml
echo.

echo [2/3] Crawling Dan Tri Quan Su
python VNNewsCrawler.py --config config_dantri_quansu.yml
echo.

echo [3/3] Crawling VietNamNet Quan Su
python VNNewsCrawler.py --config config_vietnamnet_quansu.yml
echo.

echo ========================================
echo Done! Check results in 'result' folder
echo ========================================
pause

