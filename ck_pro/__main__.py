#!/usr/bin/env python3
"""
Entry point for CognitiveKernel-Pro package.
Allows running with: python -m ck_pro

Delegates to cli.py for all functionality.
"""

if __name__ == "__main__":
    # Import and delegate to the main CLI
    try:
        from .cli import main
    except ImportError:
        from ck_pro.cli import main

    main()
