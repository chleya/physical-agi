# Keil 支持配置说明

## Keil 项目配置

### 自动检测

烧录工具会自动查找 Keil 项目文件:

```bash
# 项目文件
*.uvproj    # Keil uVision 5
*.uvprojx   # Keil uVision 6 (XML 格式)
```

### 手动指定

```bash
# 在代码中配置
from flash_tool import FlashConfig, KeilConfig, BuildSystem

config = FlashConfig(
    build_system=BuildSystem.KEIL_UV5,
    keil_config=KeilConfig(
        uvproj_file="Project/STM32F4.uvproj",
        target="Flash",
        device="STM32F407VGTx"
    )
)
```

### 交互模式

```
烧录工具会检测 Keil 项目并自动使用。
```

## Keil 安装要求

### MDK Community Edition (免费)

下载: https://www.keil.com/download/

支持:
- STM32F0, STM32F1, STM32F2, STM32F3, STM32F4, STM32L0, STM32L1, STM32L4+
- 最多 32KB 代码限制 (足够大多数项目)

### 查找路径

工具会按以下顺序查找 Keil:

1. `C:\Keil_v5\UV4\UV4.exe`
2. `C:\Keil_v6\UV4\UV4.exe`
3. `C:\Program Files\Keil\UV4\UV4.exe`
4. 环境变量 `KEIL_PATH`
5. 环境变量 `UV4_PATH`

### 环境变量设置

```bash
# PowerShell
$env:KEIL_PATH = "C:\Keil_v5\UV4"

# CMD
set KEIL_PATH=C:\Keil_v5\UV4
```

## 构建命令

### Keil uVision 5/6

```bash
# 交互模式
UV4.exe -b -t Flash project.uvprojx

# 参数说明
-b      批量构建
-t      目标 (Flash, Debug)
-j0     最大并行数
```

### 输出文件

构建成功后生成:

```
Project/
├── STM32F4.elf      # ELF 文件 (用于 OpenOCD)
├── STM32F4.hex      # HEX 文件
└── STM32F4.bin      # BIN 文件
```

## 常见问题

### Q: 找不到 UV4.exe

```bash
# 检查安装路径
dir C:\Keil_v5\UV4\UV4.exe

# 如果不存在，下载安装 MDK
# https://www.keil.com/download/
```

### Q: 构建报错

```bash
# 检查许可证
# MDK Community Edition 可能有代码大小限制

# 尝试清理后重建
UV4.exe -t Flash project.uvprojx -c
```

### Q: STM32 芯片不支持

```bash
# 安装设备包
# Keil MDK -> Pack Installer
# 安装 STM32F4xx_DFP
```

## 替代方案

如果不想安装 Keil，可以使用:

### 1. PlatformIO (推荐)

```bash
pip install platformio
pio init --board STM32F407VG
pio run -e genericSTM32F407VG
```

### 2. STM32CubeIDE

免费官方 IDE:
- https://www.st.com/stm32cubeide

### 3. ARM GCC + CMake

```bash
# 安装 ARM GCC
# https://developer.arm.com/downloads/-/gnu-rm

# 构建
cmake -DCMAKE_TOOLCHAIN_FILE=cmake/STM32F4.cmake ..
make
```

## 完整配置示例

```python
from flash_tool import FlashConfig, KeilConfig, BuildSystem

# Keil 配置
config = FlashConfig(
    build_system=BuildSystem.KEIL_UV5,
    stm32_elf="Project/Objects/STM32F4.elf",
    keil_config=KeilConfig(
        uvproj_file="Project/STM32F4.uvprojx",
        target="Flash",
        device="STM32F407VGTx"
    )
)
```

---

最后更新: 2026-02-18
