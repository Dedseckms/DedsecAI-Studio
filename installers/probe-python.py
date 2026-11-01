"""Check capabilities without shell-quoted Python source on Windows PowerShell 5."""
import sqlite3
import sys
import tkinter
sqlite3.connect(':memory:').execute('CREATE VIRTUAL TABLE t USING fts5(x)')
raise SystemExit(0 if sys.version_info >= (3,10) else 1)
