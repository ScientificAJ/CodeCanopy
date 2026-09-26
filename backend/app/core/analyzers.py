from app.analyzers.python_analyzer import PythonAnalyzer
from app.services.analyzer_service import AnalyzerService

analyzer_service = AnalyzerService(analyzers=(PythonAnalyzer(),))
