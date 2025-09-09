---
inclusion: always
---

# CLI Command Guidelines

## Command Execution Principles

### Break Down Complex Operations
- Execute commands in separate, focused steps rather than chaining multiple operations
- Use individual tool calls instead of combining commands with `&&`, `||`, or `;`
- Prefer multiple simple commands over single complex ones

### Virtual Environment Commands
- Always use `./venv/bin/python` for Python execution
- Keep pip commands simple: `./venv/bin/pip install package_name`
- Avoid complex pip operations with multiple flags in single commands

### Testing Commands
```bash
# Preferred: Simple, focused commands
./venv/bin/python -m pytest tests/test_accounts.py
./venv/bin/python -m pytest --cov

# Avoid: Complex multi-option commands
./venv/bin/python -m pytest tests/ --cov --cov-report=html --verbose --tb=short
```

### Database Operations
```bash
# Preferred: Individual operations
./venv/bin/python scripts/init_db.py
./venv/bin/python scripts/generate_demo_database.py

# Avoid: Chained database operations
./venv/bin/python scripts/init_db.py && ./venv/bin/python scripts/generate_demo_database.py
```

### File Operations
- Use individual file tool calls instead of complex find/grep combinations
- Prefer reading files directly rather than using `cat` with pipes
- Use specific tools for file search instead of complex shell patterns

### Application Management
```bash
# Preferred: Simple startup
./venv/bin/python scripts/start.py

# Avoid: Complex startup with multiple environment variables
ENV_VAR1=value ENV_VAR2=value ./venv/bin/python scripts/start.py --debug --port 5000 --host 0.0.0.0
```

### Testing and Functionality Verification
- Create temporary scripts for complex testing scenarios instead of long CLI commands
- Use Python scripts in the `scripts/` directory for multi-step operations
- Prefer programmatic testing over complex shell command combinations

## Command Complexity Limits
- Maximum 3 arguments per command
- No command chaining operators
- No complex shell redirections or pipes
- Use tool-specific operations instead of generic shell commands
