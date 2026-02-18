@echo off
REM ============ 完整硬件开发工作流 ============
REM 文件: run_full_dev_workflow.bat
REM 用途: 一键执行所有开发步骤

chcp 65001 >nul
echo.
echo ============================================
echo   NCA-Mesh 完整开发工作流 v1.0
echo ============================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装
    pause
    exit /b 1
)

REM 安装依赖
echo [1/6] 安装依赖...
pip install pyserial pandas matplotlib opencv-python -q
echo.

REM 编译
echo [2/6] 编译固件...
if exist "build.bat" (
    call build.bat
) else if exist "CMakeLists.txt" (
    echo 使用CMake构建...
    mkdir build 2>nul
    cd build
    cmake .. >nul
    make >nul 2>&1
    cd ..
) else (
    echo [WARN] 未找到构建脚本，跳过编译
)

REM 烧录
echo [3/6] 烧录固件...
python hardware_test\hardware_auto_test.py --id 01 --mode quick
echo.

REM 启动实时监控
echo [4/6] 启动实时监控 (5秒后开始)...
timeout /t 5 /nobreak >nul
start "Monitor" python hardware_test\realtime_monitor.py --port COM3 --log logs\data_01.csv

REM 启动视频录制
echo [5/6] 启动视频录制...
if not exist "videos" mkdir videos
start "Video" python hardware_test\video_capture.py --output videos\test_01.mp4

REM 等待测试完成
echo [6/6] 等待测试完成 (30秒)...
timeout /t 30 /nobreak >nul

REM 停止录制
taskkill /fi "WindowTitle eq Monitor*" >nul 2>&1
taskkill /fi "WindowTitle eq Video*" >nul 2>&1

REM 分析数据
echo.
echo [分析] 分析测试数据...
if exist "logs\data_01.csv" (
    python hardware_test\data_analyzer.py logs\data_01.csv --plot
)

echo.
echo ============================================
echo   开发工作流完成!
echo ============================================
echo.
echo 生成的文件:
echo   - logs\data_01.csv      ^: 实时数据
echo   - videos\test_01.mp4     ^: 视频录制
echo   - plots\*.png            ^: 分析图表
echo.
pause
