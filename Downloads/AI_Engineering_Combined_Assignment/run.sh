#!/usr/bin/env bash
set -e
python -m uvicorn app.main:app --reload
