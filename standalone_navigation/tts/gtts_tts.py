"""
Google Text-to-Speech (gTTS) Implementation
"""
import threading
from typing import Optional
from .base_tts import BaseTTS

try:
    from gtts import gTTS
    import pygame
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    gTTS = None
    pygame = None

class GTTSTTS(BaseTTS):
    """Google Text-to-Speech implementation"""
    
    def __init__(self, language: str = 'en', slow: bool = False):
        """
        Initialize gTTS
        
        Args:
            language: Language code
            slow: Whether to speak slowly
        """
        if not GTTS_AVAILABLE:
            raise ImportError("gTTS and pygame are required. Install with: pip install gtts pygame")
        
        super().__init__(language, slow)
        self.logger.info("Initialized gTTS")
    
    def speak(self, text: str) -> Optional[str]:
        """
        Convert text to speech using gTTS
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Path to generated audio file or None if failed
        """
        try:
            processed_text = self.preprocess_text(text)
            if not processed_text:
                return None
            
            # Generate audio file
            tts = gTTS(text=processed_text, lang=self.language, slow=self.slow)
            
            # Save to temporary file
            audio_path = self.get_temp_file_path('.mp3')
            tts.save(audio_path)
            
            self.logger.info(f"Generated TTS audio: {audio_path}")
            return audio_path
            
        except Exception as e:
            self.logger.error(f"gTTS error: {e}")
            return None
    
    def speak_async(self, text: str, callback=None) -> None:
        """
        Convert text to speech asynchronously
        
        Args:
            text: Text to convert to speech
            callback: Optional callback function to call when done
        """
        def _speak_worker():
            try:
                audio_path = self.speak(text)
                if callback:
                    callback(audio_path)
            except Exception as e:
                self.logger.error(f"Async gTTS error: {e}")
                if callback:
                    callback(None)
        
        thread = threading.Thread(target=_speak_worker)
        thread.daemon = True
        thread.start()
    
    def play_audio(self, audio_path: str) -> bool:
        """
        Play audio file using pygame
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            True if played successfully, False otherwise
        """
        try:
            if not pygame:
                self.logger.error("pygame not available for audio playback")
                return False
            
            pygame.mixer.init()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Audio playback error: {e}")
            return False
    
    def speak_and_play(self, text: str) -> bool:
        """
        Convert text to speech and play it immediately
        
        Args:
            text: Text to convert to speech
            
        Returns:
            True if successful, False otherwise
        """
        try:
            audio_path = self.speak(text)
            if audio_path:
                success = self.play_audio(audio_path)
                # Clean up temp file
                self.cleanup_temp_file(audio_path)
                return success
            return False
            
        except Exception as e:
            self.logger.error(f"Speak and play error: {e}")
            return False
