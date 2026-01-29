#!/bin/bash
cd "$(dirname "$0")" || exit
./.venv/bin/python src/main.py
