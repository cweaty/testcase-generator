#!/usr/bin/env python3
import sys
try:
    import fastapi
    print(f"fastapi: {fastapi.__version__}")
    import uvicorn
    print(f"uvicorn: {uvicorn.__version__}")
    import openai
    print(f"openai: {openai.__version__}")
    import docx
    print(f"docx: OK")
    import openpyxl
    print(f"openpyxl: {openpyxl.__version__}")
    import aiosqlite
    print(f"aiosqlite: OK")
    import pydantic
    print(f"pydantic: {pydantic.__version__}")
    print("\n✅ All dependencies OK!")
except ImportError as e:
    print(f"\n❌ Import error: {e}")
    sys.exit(1)
