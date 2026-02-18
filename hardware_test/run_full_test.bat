@echo off
REM ============ 一键完整测试脚本 ============
REM 文件: run_full_test.bat
REM 用途: 插上硬件，双击运行，自动完成所有测试

chcp 65001 >nul
echo ============================================
echo   NCA-Mesh 硬件自动化测试 v1.0
echo ============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装或未在 PATH 中
    pause
    exit /b 1
)

REM 检查依赖
echo [1/4] 检查依赖...
pip install pyserial pandas -q
if errorlevel 1 (
    echo [WARN] 安装依赖失败，请手动执行: pip install pyserial pandas
)

REM 运行测试
echo [2/4] 启动硬件测试框架...
echo.
python hardware_test\hardware_auto_test.py --id 01 --mode full
set TEST_RESULT=%errorlevel%

echo.
echo [3/4] 打开测试报告...
if exist "reports" (
    for /f "delims=" %%i in ('dir /b /od reports\device_*_*.html') do set LATEST_REPORT=%%i
    if defined LATEST_REPORT (
        echo 打开报告: reports\%LATEST_REPORT%
        start "" "reports\%LATEST_REPORT%"
    )
)

echo.
echo ============================================
if %TEST_RESULT% == 0 (
    echo   🎉 测试通过!
) else if %TEST_RESULT% == 1 (
    echo   ⚠️  部分测试失败，请查看报告
) else (
    echo   ❌ 测试失败
)
echo ============================================
echo.
echo 提示:
echo   - 查看详细报告: reports\device_*.html
echo   - 查看CSV数据: reports\device_*.csv
echo   - 修改设备配置: 编辑本脚本或使用命令行参数
echo.
pause
