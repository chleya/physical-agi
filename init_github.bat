@echo off
REM ========================================
REM Physical-AGI GitHub 项目初始化
REM ========================================

echo.
echo ========================================
echo   Physical-AGI GitHub 项目初始化
echo ========================================

REM 检查是否在 git 仓库中
if not exist ".git" (
    echo [1/5] 初始化 Git 仓库...
    git init
) else (
    echo [1/5] Git 仓库已存在
)

REM 添加所有文件
echo [2/5] 添加文件到 Git...
git add -A

REM 创建初始提交
echo [3/5] 创建初始提交...
git commit -m "feat: 初始提交 - Physical-AGI 项目

- 物理引擎核心模块
- 演化算法框架
- 硬件工具链
- 多芯片支持
- GitHub Actions CI/CD
- 测试框架
- 完整文档
"

REM 设置主分支名
echo [4/5] 设置主分支...
git branch -M main

REM 提示下一步
echo.
echo ========================================
echo   下一步操作
echo ========================================
echo.
echo 1. 在 GitHub 上创建仓库:
echo    https://github.com/new
echo.
echo 2. 添加远程仓库:
echo    git remote add origin https://github.com/yourusername/physical-agi.git
echo.
echo 3. 推送代码:
echo    git push -u origin main
echo.
echo ========================================

:end
pause
