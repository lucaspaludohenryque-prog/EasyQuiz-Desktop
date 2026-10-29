"""
Módulo Wrapper de Compatibilidade - CerebroManager -> BrainStorage
Garante retrocompatibilidade imediata com a arquitetura v3.9.0 e gui.py.
"""

from brain_storage import BrainStorage, QuestionSessionRecord

# Exportação direta
CerebroManager = BrainStorage

__all__ = ["BrainStorage", "CerebroManager", "QuestionSessionRecord"]
