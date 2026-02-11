# Contributing to Omni Quantum Elite

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

---

## Getting Started

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your changes
4. **Make changes** following our standards
5. **Test** your changes
6. **Submit** a pull request

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/omni-quantum-elite.git
cd omni-quantum-elite

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes, then commit
git add .
git commit -m "feat: add your feature description"

# Push and create PR
git push origin feature/your-feature-name
```

---

## Coding Standards

### Python
- **Formatter:** Black (line length 100)
- **Linter:** Ruff
- **Type hints:** Required for all functions
- **Docstrings:** Google style

```python
def process_request(data: Dict[str, Any], timeout: int = 30) -> ProcessResult:
    """Process an incoming request.

    Args:
        data: Request data dictionary.
        timeout: Request timeout in seconds.

    Returns:
        ProcessResult with status and response.

    Raises:
        ValidationError: If data is invalid.
    """
    ...
```

### TypeScript/JavaScript
- **Formatter:** Prettier
- **Linter:** ESLint
- **Types:** TypeScript required for new code

### Docker
- Use multi-stage builds
- Pin image versions
- Add health checks
- Follow naming convention: `omni-{service}`

### Commits
Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature
fix: fix bug in X
docs: update documentation
refactor: refactor X without changing behavior
test: add tests for X
chore: update dependencies
```

---

## Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Ensure CI passes** (all checks green)
4. **Request review** from maintainers
5. **Address feedback** promptly

### PR Title Format
```
feat(service): add feature description
fix(service): fix bug description
docs: update X documentation
```

### PR Description Template
```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed code
- [ ] Added tests
- [ ] Updated documentation
- [ ] CI passes
```

---

## Testing

### Running Tests
```bash
# Python tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific test file
pytest tests/test_orchestrator.py -v
```

### Writing Tests
- Place tests in `tests/` directory
- Name files `test_*.py`
- Use fixtures for common setup
- Mock external services

---

## Documentation

- Update relevant docs with code changes
- Use Markdown for documentation
- Include code examples where helpful
- Keep language clear and concise

---

## Questions?

- Open a GitHub issue
- Post in Mattermost #development
- Email maintainers

---

*Thank you for contributing to Omni Quantum Elite!*
