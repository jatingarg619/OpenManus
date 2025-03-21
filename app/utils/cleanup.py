import os
from pathlib import Path
import time

def cleanup_temp_files(temp_dir: str, max_age: int = 3600):
    """Clean up temporary files older than max_age seconds"""
    try:
        current_time = time.time()
        for file in Path(temp_dir).glob('search_results_*.html'):
            if current_time - file.stat().st_mtime > max_age:
                file.unlink()
    except Exception as e:
        print(f"Error cleaning up temp files: {e}") 