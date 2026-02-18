#!/usr/bin/env bash
# GitHub 项目初始化脚本

echo "========================================"
echo "  Physical-AGI GitHub 项目初始化"
echo "========================================"

# 检查是否在 git 仓库中
if [ ! -d ".git" ]; then
    echo "[1/6] 初始化 Git 仓库..."
    git init
else
    echo "[1/6] Git 仓库已存在"
fi

# 添加所有文件
echo "[2/6] 添加文件到 Git..."
git add -A

# 创建初始提交
echo "[3/6] 创建初始提交..."
git commit -m "feat: 初始提交 - Physical-AGI 项目

- 物理引擎核心模块
- 演化算法框架
- 硬件工具链 (flash, wire_check, vision, monitor 等)
- 多芯片支持 (STM32F4xx, STM32H7xx, ESP32 等)
- GitHub Actions CI/CD 配置
- 测试框架
- 完整文档

详见: https://github.com/yourusername/physical-agi"

# 设置主分支名为 main
echo "[4/6] 设置主分支..."
git branch -M main

# 提示用户添加远程仓库
echo "[5/6] 下一步操作:"
echo ""
echo "请执行以下命令来推送代码:"
echo ""
echo "  1. 在 GitHub 上创建仓库: https://github.com/new"
echo "     - Repository name: physical-agi"
echo "     - Description: Physical-AGI: Edge Evolution Embodied Swarm"
echo "     - Public 或 Private"
echo ""
echo "  2. 添加远程仓库:"
echo "     git remote add origin https://github.com/yourusername/physical-agi.git"
echo ""
echo "  3. 推送代码:"
echo "     git push -u origin main"
echo ""
echo "========================================"

# 打开 GitHub 创建页面
if command -v xdg-open &> /dev/null; then
    read -p "是否打开 GitHub 创建页面? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        xdg-open https://github.com/new
    fi
fi

echo "========================================"
echo "初始化完成!"
echo "========================================"
