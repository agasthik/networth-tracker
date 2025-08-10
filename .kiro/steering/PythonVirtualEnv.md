---
inclusion: always
---

# Python Virtual Environment Requirements

## Critical Command Execution Rules

**ALWAYS use the virtual environment** - Never execute Python commands directly from the system Python installation.

### Virtual Environment Path
- Location: `./venv/bin/` (relative to project root)
- All Python commands must be prefixed with `./venv/bin/`

### Required Command Patterns

#### Python Execution
```bash
# Correct
./venv/bin/python script_name.py
./venv/bin/python -m module_name

# Incorrect
python script_name.py
python3 script_name.py
```

#### Package Management
```bash
# Correct
./venv/bin/python -m pip install package_name
./venv/bin/pip install package_name

# Incorrect
pip install package_name
pip3 install package_name
```

#### Testing
```bash
# Correct
./venv/bin/python -m pytest
./venv/bin/pytest tests/

# Incorrect
pytest
python -m pytest
```

### Common Project Commands
- Database initialization: `./venv/bin/python scripts/init_db.py`
- Demo data generation: `./venv/bin/python scripts/generate_demo_database.py`
- Application startup: `./venv/bin/python scripts/start.py`
- Test execution: `./venv/bin/python -m pytest`

### Working Directory
Always execute commands from the project root directory where `venv/` folder is located.