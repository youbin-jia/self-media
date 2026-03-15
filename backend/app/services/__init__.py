# backend/app/services/__init__.py
"""Services Package"""
from app.services.llm_provider import LLMProvider, get_llm_provider
from app.services.quality_detector import QualityDetector, get_quality_detector
from app.services.script_generator import ScriptGenerator
from app.services.topic_monitor import TopicMonitor
from app.services.material_collector import MaterialCollector

__all__ = [
    'LLMProvider',
    'get_llm_provider',
    'QualityDetector',
    'get_quality_detector',
    'ScriptGenerator',
    'TopicMonitor',
    'MaterialCollector',
]
