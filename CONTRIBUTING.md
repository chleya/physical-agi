# Contributing to Physical-AGI

Thank you for your interest in contributing! This document provides guidelines for contributing.

## Quick Start

1. Fork the repository
2. Clone your fork locally
3. Create a feature branch
4. Make your changes
5. Push to GitHub
6. Create a Pull Request

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- (Optional) STM32 toolchain for hardware builds

### Install Development Dependencies

```bash
pip install -q pytest pytest-cov flake8 black
```

## Coding Style

### Python

We follow PEP 8 with some modifications:

- Line length: 100 characters
- Use Black for formatting
- Use type hints

### Code Formatting

```bash
# Format code
black .

# Check formatting
black --check .
```

### Linting

```bash
flake8 . --count --show-source --statistics
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=term

# Run specific test
pytest tests/test_physics.py -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Use pytest framework
- Follow naming pattern: `test_*.py`

## Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools

Examples:

```
feat(hardware): add STM32H7 support
fix(evolution): correct mutation rate calculation
docs(readme): update installation instructions
```

## Project Structure

```
physical-agi/
├── core/                  # Core modules
│   ├── physics_engine_*.py
│   └── nca_network.py
├── hardware_test/        # Hardware tools
├── tests/                # Unit tests
├── simulator_v2.py      # Evolution simulator
├── docs/                # Documentation
└── hardware/             # Hardware code
```

## Hardware Development

### Adding New Hardware Support

1. Add chip configuration to `hardware_test/stm32_chip.py`
2. Add device template to `hardware_test/device_config.py`
3. Update `README.md` with supported devices
4. Add tests for the new hardware

### Adding New Tools

1. Create the tool in `hardware_test/`
2. Add tests in `tests/`
3. Update `README.md` with usage examples
4. Add to `hardware_toolkit.py` if applicable

## Documentation

- Update `README.md` for new features
- Add docstrings to new functions
- Use Markdown for documentation

## Submitting Changes

1. Ensure all tests pass
2. Update documentation
3. Create a Pull Request with:
   - Clear title
   - Detailed description
   - Link to related issues

## Code Review

- All pull requests require review
- Address review comments
- Keep changes focused

## Questions?

Open an issue for discussion.
