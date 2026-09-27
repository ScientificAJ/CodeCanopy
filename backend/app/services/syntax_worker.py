"""Trusted parser subprocess. Reads text on stdin; never imports repository code."""
import json
from pathlib import Path
import sys

try:
    import resource
except ImportError:
    resource = None

if resource is not None:
    resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024, 384 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (2, 3))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.analyzers.python_analyzer import PythonAnalyzer
from app.analyzers.tree_sitter_analyzer import TreeSitterAnalyzer

if __name__ == '__main__':
    payload = json.load(sys.stdin)
    language = payload['language']
    if language == 'python':
        result = PythonAnalyzer().analyze(payload['text'], payload['path'], payload['size'])
        parser_name = 'python-ast'
    else:
        result = TreeSitterAnalyzer().analyze(payload['text'], payload['path'], language, payload['size'])
        parser_name = 'tree-sitter'
    from app.analyzers.dependency_syntax import extract_dependencies
    result.dependency_syntax = extract_dependencies(payload['text'], payload['path'], language)
    serialized = result.model_dump()
    serialized['dependency_syntax'] = result.dependency_syntax
    serialized['parser'] = parser_name
    serialized['references'] = result.references
    for function_data, function in zip(serialized['functions'], result.functions):
        function_data.update({
            'calls': function.calls,
            'structural_hash': function.structural_hash,
            'structural_signature': function.structural_signature,
        })
    print(json.dumps(serialized, ensure_ascii=True))
