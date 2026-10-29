"""
Wrapper de Compatibilidade - ai_vision -> ai_service
"""

from ai_service import AIService, QuizSolutionResult

# Alias de compatibilidade total
AIVisionService = AIService
VisionAnalysisResult = QuizSolutionResult

__all__ = ["AIService", "AIVisionService", "QuizSolutionResult", "VisionAnalysisResult"]
