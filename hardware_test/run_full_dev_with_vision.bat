@echo off
REM ============ 完整硬件开发流程 (带视觉检测) ============
REM 文件: run_full_dev_with_vision.bat
REM 用途: 包含视觉检测的完整开发流程

chcp 65001 >nul
echo.
echo ============================================
echo   NCA-Mesh 完整开发流程 (带视觉检测) v1.0
echo ============================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装
    pause
    exit /b 1
)

echo [1/7] 检查依赖...
pip install pyserial pandas matplotlib opencv-python numpy -q
echo.

REM 连线检测
echo [2/7] ⚠️ 连线检测 (通电前必用!)...
python hardware_test\wire_check.py --port COM3
if errorlevel 1 (
    echo [WARN] 连线有问题，但仍继续...
)
echo.

REM 启动视觉检测 (后台)
echo [3/7] 启动视觉检测...
if exist "hardware_test\vision_inspector.py" (
    start "Vision" python hardware_test\vision_inspector.py --camera 0 --openclaw-mode
    echo [INFO] 视觉检测已启动
    timeout /t 3 /nobreak >nul
) else (
    echo [WARN] 视觉检测模块不存在，跳过
)

REM 编译
echo [4/7] 编译固件...
if exist "build.bat" (
    call build.bat
) else (
    echo [WARN] 未找到构建脚本，跳过编译
)

REM 烧录
echo [5/7] 烧录固件...
python hardware_test\hardware_auto_test.py --id 01 --mode quick
echo.

REM 启动实时监控
echo [6/7] 启动实时监控 (5秒后开始)...
timeout /t 5 /nobreak >nul
start "Monitor" python hardware_test\realtime_monitor.py --port COM3 --log logs\data_01.csv

REM 等待测试
echo [7/7] 等待测试完成 (20秒)...
timeout /t 20 /nobreak >nul

REM 停止所有检测
taskkill /fi "WindowTitle eq Vision*" >nul 2>&1
taskkill /fi "WindowTitle eq Monitor*" >nul 2>&1

REM 数据分析
echo.
echo [分析] 分析测试数据...
if exist "logs\data_01.csv" (
    python hardware_test\data_analyzer.py logs\data_01.csv --plot --hotfix
)

REM 获取视觉状态
echo.
echo [视觉] 获取视觉检测结果...
if exist "hardware_test\vision_openclaw.py" (
    python -c "
from hardware_test.vision_openclaw import OpenClawVision
v = OpenClawVision()
try:
    v.start(blocking=False)
    time.sleep(2)
    status = v.check()
    print(f'视觉状态: {v.get_status_message()}')
    v.stop()
except Exception as e:
    print(f'视觉检测跳过: {e}')
"
)

echo.
echo ============================================
echo   开发流程完成!
echo ============================================
echo.
echo 生成的文件:
echo   - logs\data_01.csv      ^: 实时数据
echo   - plots\*.png           ^: 分析图表
echo   - reports\*.html        ^: 测试报告
echo.
echo 提示:
echo   - 查看视觉检测: 运行 vision_inspector.py
echo   - 查看实时监控: 运行 realtime_monitor.py
echo   - 进行数据分析: 运行 data_analyzer.py
echo.
pause
