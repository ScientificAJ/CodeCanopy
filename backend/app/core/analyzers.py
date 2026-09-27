from app.analyzers.java_analyzer import JavaAnalyzer
from app.analyzers.js_analyzer import JSAnalyzer
from app.analyzers.python_analyzer import PythonAnalyzer
from app.services.analyzer_service import AnalyzerService

analyzer_service = AnalyzerService(analyzers=(PythonAnalyzer(), JSAnalyzer(), JavaAnalyzer()))
