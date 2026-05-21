# Contributing to Asubarnipal

Thank you for your interest in contributing to Asubarnipal! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the project

## Getting Started

### Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/VicenteVila/Asubarnipal.git
cd Asubarnipal

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=term-missing

# Run specific test module
python -m pytest tests/test_llm_router.py -v
```

## Development Workflow

### Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code |
| `develop` | Integration branch for features |
| `feature/*` | New features |
| `fix/*` | Bug fixes |
| `docs/*` | Documentation updates |

### Creating a Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code style changes (formatting, no logic change) |
| `refactor` | Code refactoring |
| `perf` | Performance improvements |
| `test` | Adding or updating tests |
| `ci` | CI/CD configuration changes |
| `chore` | Maintenance tasks |
| `revert` | Reverting a previous commit |

#### Examples

```bash
feat: add vault export functionality
fix: correct wiki search pagination
docs: update README with new commands
refactor: extract handler logic to separate module
test: add integration tests for H-Mem
perf: optimize FAISS index rebuild
ci: add GitHub Actions workflow
chore: update dependencies
```

## Code Standards

### Python Style

- **Line length**: 100 characters maximum
- **Indentation**: 4 spaces (no tabs)
- **Naming**:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants
- **Imports**: Order by stdlib, third-party, local

### Docstrings

All public functions and classes must have docstrings:

```python
def search_wiki(query: str, limit: int = 10) -> list[dict]:
    """Search wiki notes by query.

    Args:
        query: Search query string.
        limit: Maximum number of results to return.

    Returns:
        List of matching wiki notes with scores.

    Raises:
        ValueError: If query is empty.
    """
    pass
```

### Type Hints

Use type hints for function signatures:

```python
def process_memory(text: str, importance: str = "medium") -> dict[str, Any]:
    pass
```

## Pull Request Process

### Before Submitting

1. [ ] All tests pass (`python -m pytest tests/ -v`)
2. [ ] Code follows project style
3. [ ] New features have tests
4. [ ] Documentation is updated
5. [ ] Commit messages follow convention

### PR Template

```markdown
## Description

Brief description of the change.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

Describe how the change was tested.

## Related Issues

Closes #123
```

## Testing Guidelines

### Writing Tests

- Use `unittest` framework (consistent with existing tests)
- Mock external services (Ollama, Gemini, Brave)
- Test both success and error cases
- Keep tests focused and isolated

### Example Test

```python
import unittest
from unittest.mock import Mock, patch

class TestMyFeature(unittest.TestCase):
    """Test class for my_feature."""

    def test_success_case(self):
        # Arrange
        from module import my_function

        # Act
        result = my_function("valid_input")

        # Assert
        self.assertEqual(result, "expected_output")

    def test_error_case(self):
        from module import my_function

        with self.assertRaises(ValueError):
            my_function("invalid_input")
```

## Debugging

### Viewing Logs

```bash
# Real-time logs
tail -f data/agente.log

# Filter errors
tail -50 data/agente.log | grep ERROR
```

### Common Issues

| Issue | Solution |
|-------|----------|
| ImportError in tests | Add `sys.path.insert(0, os.path.dirname(__file__))` |
| Async in tests | Use `asyncio.run()` or `loop.run_until_complete()` |
| Mock config | Patch before importing the module |

## Architecture Overview

```
Telegram Bot → Handlers → Agent Service → LLM Router → Ollama/Gemini
                                    → Skill Registry → 50+ Skills
                                    → RAG Engine → FAISS + SQLite
                                    → H-Mem → Tree + Graph
```

## Resources

- [Python Documentation](https://docs.python.org/3/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Ollama Documentation](https://ollama.ai/docs)

## Questions?

Open an issue on GitHub for questions or suggestions.
