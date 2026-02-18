# Physical-AGI: Edge Evolution Embodied Swarm

<div align="center">

**Physical-AGI: Edge Evolution Embodied Swarm**

*v5 hardware + DancingNCA algorithm → autonomous robot swarm*

[![CI/CD](https://github.com/yourusername/physical-agi/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/yourusername/physical-agi/actions)
[![Coverage](https://codecov.io/gh/yourusername/physical-agi/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/physical-agi)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

</div>

---

## Overview

Physical-AGI is an edge computing framework for autonomous robot swarms. It combines:

- **Physics Engine**: Real-time physics simulation
- **Evolution Algorithm**: Genetic evolution of neural networks
- **NCA Networks**: Neural Cellular Automata for decentralized control
- **Hardware Tools**: Complete development and debugging toolchain

### Core Philosophy

> "Robust consensus over perfect consensus"

## Features

### 🧠 Evolution System
- Genetic algorithm with elite selection
- Configurable mutation rates
- Real-time fitness tracking
- Multi-objective optimization

### 🔧 Physics Engine
- 2D/3D physics simulation
- Collision detection (AABB + Circle)
- Friction and restitution models
- Robot joint constraints

### 📦 Hardware Tools
| Tool | Purpose |
|------|---------|
| `flash_tool.py` | Build + Flash + Test |
| `wire_check.py` | Wiring verification |
| `vision_inspector.py` | Visual inspection |
| `realtime_monitor.py` | Real-time data |
| `ina219_monitor.py` | Current monitoring |
| `gdb_controller.py` | GDB debugging |
| `ota_updater.py` | Wireless OTA updates |

### 📱 Supported Hardware

| Chip | Flash | RAM | Cortex |
|------|--------|-----|---------|
| STM32F407VG | 1MB | 192KB | M4 |
| STM32F103RB | 128KB | 20KB | M3 |
| STM32H743ZI | 2MB | 1MB | M7 |
| STM32G431CB | 128KB | 32KB | M4 |
| ESP32 | 4MB | 520KB | M4 |

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/physical-agi.git
cd physical-agi

# Install Python dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov flake8 black
```

### Basic Usage

```python
from simulator_v2 import Simulation, NCANetwork

# Create evolution simulation
sim = Simulation({
    'num_agents': 10,
    'task': 'push',
    'generations': 10
})

# Run evolution
history = sim.evolve(generations=10)
```

### Hardware Tools

```bash
# Check wiring before powering on
python hardware_test/wire_check.py --port COM3

# Flash firmware
python hardware_test/flash_tool.py --auto

# Monitor real-time data
python hardware_test/realtime_monitor.py --port COM3
```

## Project Structure

```
physical-agi/
├── core/                    # Core modules
│   ├── physics_engine_*.py  # Physics simulation
│   ├── nca_network.py      # Neural network
│   ├── signal_processor.py  # RSSI processing
│   └── state_machine.py     # FSM
│
├── hardware_test/           # Hardware tools
│   ├── flash_tool.py        # Build & flash
│   ├── wire_check.py        # Wiring check
│   ├── vision_inspector.py  # Visual inspection
│   ├── realtime_monitor.py  # Data monitor
│   ├── ina219_monitor.py   # Current monitor
│   ├── gdb_controller.py   # GDB debugging
│   ├── ota_updater.py      # OTA updates
│   ├── stm32_chip.py       # Chip database
│   └── device_config.py     # Device templates
│
├── tests/                  # Unit tests
│   ├── test_physics.py
│   └── ...
│
├── simulator_v2.py         # Evolution simulator
├── evolve_*.py             # Evolution modules
└── docs/                   # Documentation
```

## Documentation

- [README.md](README.md) - Chinese documentation
- [docs/](docs/) - Additional docs
- [hardware_test/](hardware_test/) - Tool documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- DancingNCA algorithm research
- SEL-Lab framework
- Evo-Swarm project

---

<div align="center">

**Built with ❤️ for the future of robotics**

</div>
