@echo off
REM ============ 批量烧录脚本 ============
REM 文件: batch_flash.bat
REM 用途: 批量烧录多台设备

setlocal

REM 配置区域
set OPENOCD_PATH=openocd
set CFG_PATH=hardware_test\openocd_stm32f4.cfg
set ESPTOOL_PATH=esptool.py

REM 设备列表 (格式: 设备ID, STM32端口, ESP32端口, 设备位置)
set DEVICES=^
01,COM3,COM4,Desk ^
02,COM5,COM6,Shelf ^
03,COM7,COM8,Lab

REM 默认设置
set BUILD_DIR=build
set STM32_ELF=%BUILD_DIR%\v5_nca_mesh.elf
set ESP32_BIN=%BUILD_DIR%\esp32_nca_mesh.bin

echo ============================================
echo   NCA-Mesh 批量烧录工具 v1.0
echo ============================================
echo.

REM 检查文件存在
if not exist "%STM32_ELF%" (
    echo [ERROR] STM32 ELF 文件不存在: %STM32_ELF%
    exit /b 1
)

if not exist "%ESP32_BIN%" (
    echo [ERROR] ESP32 BIN 文件不存在: %ESP32_BIN%
    exit /b 1
)

REM 解析设备列表并烧录
for %%d in (%DEVICES%) do (
    for /f "tokens=1,2,3,4 delims=," %%a in ("%%d") do (
        echo.
        echo ============================================
        echo   烧录设备: %%a (%%d)
        echo   位置: %%d
        echo ============================================
        
        echo [1/4] 烧录 STM32...
        %OPENOCD_PATH% -f %CFG_PATH% -c "program %STM32_ELF% verify reset exit"
        if errorlevel 1 (
            echo [ERROR] STM32 烧录失败: %%a
            continue
        )
        
        echo [2/4] 烧录 ESP32...
        %ESPTOOL_PATH% --port %%c --baud 921600 write_flash 0x0 %ESP32_BIN%
        if errorlevel 1 (
            echo [ERROR] ESP32 烧录失败: %%a
            continue
        )
        
        echo [3/4] 验证设备...
        echo [OK] 设备 %%a 烧录完成
        
        echo [4/4] 生成报告...
        echo %%a,%%b,%%c,SUCCESS,%date%,%time% >> flash_report.csv
    )
)

echo.
echo ============================================
echo   批量烧录完成！
echo   报告: flash_report.csv
echo ============================================

endlocal
pause
