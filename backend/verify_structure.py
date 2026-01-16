#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple verification script that checks backend structure without importing dependencies.
"""

import os
import sys

def verify_structure():
    """Verify backend directory structure and file existence."""
    print("=" * 60)
    print("EURABAY Living System - Structure Verification")
    print("=" * 60)
    print()

    # Required files
    required_files = [
        "backend/app/__init__.py",
        "backend/app/main.py",
        "backend/app/core/__init__.py",
        "backend/app/core/config.py",
        "backend/app/core/logging.py",
        "backend/app/api/__init__.py",
        "backend/app/api/ws.py",
        "backend/app/api/rest.py",
        "backend/app/models/__init__.py",
        "backend/app/services/__init__.py",
        "backend/app/utils/__init__.py",
        "backend/app/tests/__init__.py",
        "backend/requirements.txt",
        "backend/.env",
        "backend/.env.example",
        "backend/Dockerfile",
        "backend/docker-compose.yml",
        "backend/start.sh",
        "backend/start.bat",
    ]

    print("Checking files:")
    all_exist = True
    for file_path in required_files:
        exists = os.path.exists(file_path)
        status = "[OK]" if exists else "[MISSING]"
        print(f"  {status} {file_path}")
        if not exists:
            all_exist = False

    print()

    # Check Python syntax
    print("Checking Python syntax:")
    py_files = [
        "backend/app/main.py",
        "backend/app/core/config.py",
        "backend/app/core/logging.py",
        "backend/app/api/ws.py",
        "backend/app/api/rest.py",
    ]

    syntax_ok = True
    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                compile(f.read(), py_file, 'exec')
            print(f"  [OK] {py_file}")
        except SyntaxError as e:
            print(f"  [ERROR] {py_file}: {e}")
            syntax_ok = False

    print()

    if all_exist and syntax_ok:
        print("=" * 60)
        print("[SUCCESS] Structure verification complete!")
        print("=" * 60)
        print()
        print("Backend structure is properly set up.")
        print()
        print("Next steps:")
        print("1. Install dependencies: pip install -r backend/requirements.txt")
        print("2. Start the server:")
        print("   - Unix/Linux/Mac:  ./backend/start.sh")
        print("   - Windows:        backend\\start.bat")
        print("   - Manual:         uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
        print()
        print("API Documentation will be available at:")
        print("  - Swagger UI: http://127.0.0.1:8000/api/docs")
        print("  - ReDoc:      http://127.0.0.1:8000/api/redoc")
        print("  - Health:     http://127.0.0.1:8000/health")
        print()
        return True
    else:
        print("=" * 60)
        print("[FAILED] Structure verification failed!")
        print("=" * 60)
        return False

if __name__ == "__main__":
    result = verify_structure()
    sys.exit(0 if result else 1)
