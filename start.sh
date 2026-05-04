#!/bin/bash
# Start SolarCloud locally on macOS 26 + Homebrew Python.
# DYLD_LIBRARY_PATH is required because the Homebrew Python builds
# link against a newer libexpat than macOS 26's system /usr/lib/libexpat.1.dylib.
export DYLD_LIBRARY_PATH="/opt/homebrew/opt/expat/lib:$DYLD_LIBRARY_PATH"
exec venv/bin/python app.py
