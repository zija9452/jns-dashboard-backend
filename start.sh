#!/bin/bash
# Startup script for Cloud Run
# Use PORT env var set by Cloud Run, default to 8080
exec python -m uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080}
