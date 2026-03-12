#!/usr/bin/env python3
"""
AI 能力模块
向量检索、代码补全、重构建议、质量预测
"""

from .vector_store import VectorStore
from .code_completion import ProjectAwareCompletion
from .refactoring_advisor import RefactoringAdvisor, RefactoringSuggestion
from .quality_predictor import QualityPredictor, RiskAssessment

__all__ = [
    'VectorStore',
    'ProjectAwareCompletion',
    'RefactoringAdvisor',
    'RefactoringSuggestion',
    'QualityPredictor',
    'RiskAssessment',
]