"""
Base TTS Interface - Abstract base class for all TTS implementations
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

class BaseTTS(ABC):
    """Abstract base class for Text-to-Speech implementations"""
    
    def __init__(self, language: str = 'en', slow: bool = False):
        """
        Initialize the TTS
        
        Args:
            language: Language code (e.g., 'en', 'ar', 'es')
            slow: Whether to speak slowly
        """
        self.language = language
        self.slow = slow
        self.logger = logger
        self.temp_dir = tempfile.gettempdir()
    
    @abstractmethod
    def speak(self, text: str) -> Optional[str]:
        """
        Convert text to speech and return audio file path
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Path to generated audio file or None if failed
        """
        pass
    
    @abstractmethod
    def speak_async(self, text: str, callback=None) -> None:
        """
        Convert text to speech asynchronously
        
        Args:
            text: Text to convert to speech
            callback: Optional callback function to call when done
        """
        pass
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get list of supported languages
        
        Returns:
            Dictionary mapping language codes to language names
        """
        return {
            'en': 'English',
            'ar': 'Arabic',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ko': 'Korean'
        }
    
    def is_language_supported(self, language: str) -> bool:
        """
        Check if language is supported
        
        Args:
            language: Language code to check
            
        Returns:
            True if supported, False otherwise
        """
        return language in self.get_supported_languages()
    
    def set_language(self, language: str) -> bool:
        """
        Set the language for TTS
        
        Args:
            language: Language code
            
        Returns:
            True if language was set successfully, False otherwise
        """
        if self.is_language_supported(language):
            self.language = language
            return True
        return False
    
    def set_speed(self, slow: bool) -> None:
        """
        Set speech speed
        
        Args:
            slow: True for slow speech, False for normal speed
        """
        self.slow = slow
    
    def get_temp_file_path(self, extension: str = '.mp3') -> str:
        """
        Get a temporary file path for audio output
        
        Args:
            extension: File extension (default: .mp3)
            
        Returns:
            Temporary file path
        """
        import uuid
        filename = f"tts_{uuid.uuid4().hex}{extension}"
        return os.path.join(self.temp_dir, filename)
    
    def cleanup_temp_file(self, file_path: str) -> None:
        """
        Clean up temporary audio file
        
        Args:
            file_path: Path to file to delete
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
    
    def validate_text(self, text: str) -> bool:
        """
        Validate text for TTS
        
        Args:
            text: Text to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not text or not isinstance(text, str):
            return False
        
        # Check text length (most TTS services have limits)
        if len(text) > 5000:
            self.logger.warning("Text too long for TTS, truncating")
            return False
        
        return True
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text before TTS
        
        Args:
            text: Original text
            
        Returns:
            Preprocessed text
        """
        if not self.validate_text(text):
            return ""
        
        # Basic preprocessing
        processed = text.strip()
        
        # Truncate if too long
        if len(processed) > 5000:
            processed = processed[:5000] + "..."
        
        return processed
