import sys
import os

# Add parent directory to path so imports like database and templates work smoothly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel WSGI entry point
# `app` is exposed as the WSGI callable
