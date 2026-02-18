# GitHub 项目创建指南

## 快速开始

### 方式 1: 使用脚本 (推荐)

**Windows:**
```batch
init_github.bat
```

**Linux/Mac:**
```bash
chmod +x init_github.sh
./init_github.sh
```

### 方式 2: 手动

```bash
# 1. 初始化仓库
git init
git add -A
git commit -m "feat: 初始提交"

# 2. 在 GitHub 创建仓库
# 访问 https://github.com/new

# 3. 推送
git remote add origin https://github.com/yourusername/physical-agi.git
git push -u origin main
```

## 创建的 GitHub 项目文件

```
physical-agi/
├── .github/
│   ├── workflows/
│   │   └── ci-cd.yml          # CI/CD 流水线
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md      # Bug 报告模板
│       └── feature_request.md # 功能请求模板
├── .gitignore                # Git 忽略规则
├── PULL_REQUEST_TEMPLATE.md # PR 模板
├── CONTRIBUTING.md           # 贡献指南
├── requirements.txt         # Python 依赖
├── README_EN.md            # 英文 README
└── init_github.bat          # 初始化脚本
```

## GitHub Actions 流水线

### CI/CD 功能

| Job | 功能 | 触发条件 |
|-----|------|----------|
| quality | 代码检查 + 测试 | push/PR |
| build | 多构建系统验证 | quality 通过后 |
| simulation | 仿真测试 | build 通过后 |
| docs | 文档生成 | push/PR |

### 支持的构建系统

- CMake
- Keil uVision
- PlatformIO

### 徽章

在 README 中添加:

```markdown
[![CI/CD](https://github.com/yourusername/physical-agi/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/yourusername/physical-agi/actions)
```

## Issue 模板

### Bug Report

路径: `.github/ISSUE_TEMPLATE/bug_report.md`

### Feature Request

路径: `.github/ISSUE_TEMPLATE/feature_request.md`

## Pull Request 模板

路径: `.PULL_REQUEST_TEMPLATE.md`

## 贡献指南

见: `CONTRIBUTING.md`

包含:
- 开发环境设置
- 代码风格
- 测试要求
- 提交规范

## 初始设置清单

- [ ] 创建 GitHub 仓库
- [ ] 添加协作者 (可选)
- [ ] 启用 GitHub Actions
- [ ] 配置 Code Coverage (Codecov)
- [ ] 设置 GitHub Pages (可选)
- [ ] 添加仓库徽章到 README
- [ ] 创建初始 Release

## 推荐设置

### GitHub Pages

在 Settings → Pages 中启用:
- Source: Deploy from a branch
- Branch: gh-pages / (root)

### Branch Protection

在 Settings → Branches 中:
- Require pull request reviews
- Require status checks before merging

### Issues

- 启用模板
- 设置标签

## 后续步骤

1. 创建第一个 Release
2. 添加 CI/CD 徽章到 README
3. 推广项目:
   - 分享到社交媒体
   - 提交到 GitHub Trending
   - 发布到开发者社区

## 帮助

- GitHub Docs: https://docs.github.com
- GitHub Actions: https://docs.github.com/en/actions
- 贡献指南: CONTRIBUTING.md
