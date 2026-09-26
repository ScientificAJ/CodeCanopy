"""Trusted parser subprocess. Reads text on stdin; never imports repository code."""
import json
from pathlib import Path
import resource
import sys

resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024, 384 * 1024 * 1024))
resource.setrlimit(resource.RLIMIT_CPU, (2, 3))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.analyzers.python_analyzer import PythonAnalyzer

if __name__ == '__main__':
    payload = json.load(sys.stdin)
    result = PythonAnalyzer().analyze(payload['text'], payload['path'], payload['size'])
    print(result.model_dump_json())
