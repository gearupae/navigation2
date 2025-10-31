"""
TTS Module - Modular Text-to-Speech Interface
Supports multiple TTS providers with consistent interface
"""

from .base_tts import BaseTTS
from .gtts_tts import GTTSTTS
from .pyttsx3_tts import Pyttsx3TTS

__all__ = ['BaseTTS', 'GTTSTTS', 'Pyttsx3TTS']
