"""Entrypoint wrapper for packaging standalone CLI."""
import sys
from docx_a11y.cli import main

if __name__ == "__main__":
    sys.exit(main())
