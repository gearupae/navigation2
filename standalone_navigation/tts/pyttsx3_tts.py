"""
pyttsx3 TTS Implementation - Offline Text-to-Speech
"""
import threading
from typing import Optional
from .base_tts import BaseTTS

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    pyttsx3 = None

class Pyttsx3TTS(BaseTTS):
    """pyttsx3 offline TTS implementation"""
    
    def __init__(self, language: str = 'en', slow: bool = False):
        """
        Initialize pyttsx3 TTS
        
        Args:
            language: Language code
            slow: Whether to speak slowly
        """
        if not PYTTSX3_AVAILABLE:
            raise ImportError("pyttsx3 is required. Install with: pip install pyttsx3")
        
        super().__init__(language, slow)
        self.engine = pyttsx3.init()
        self._configure_engine()
        self.logger.info("Initialized pyttsx3 TTS")
    
    def _configure_engine(self):
        """Configure the TTS engine"""
        try:
            # Set speech rate
            rate = self.engine.getProperty('rate')
            if self.slow:
                self.engine.setProperty('rate', rate * 0.7)  # 30% slower
            else:
                self.engine.setProperty('rate', rate)
            
            # Set volume
            self.engine.setProperty('volume', 0.9)
            
            # Try to set language (may not work on all systems)
            voices = self.engine.getProperty('voices')
            if voices:
                # Look for voice matching the language
                for voice in voices:
                    if self.language in voice.id.lower() or self.language in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
            
        except Exception as e:
            self.logger.warning(f"Could not configure TTS engine: {e}")
    
    def speak(self, text: str) -> Optional[str]:
        """
        Convert text to speech using pyttsx3
        
        Note: pyttsx3 doesn't generate audio files, it plays directly
        This method returns a placeholder path for compatibility
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Placeholder path (pyttsx3 plays directly)
        """
        try:
            processed_text = self.preprocess_text(text)
            if not processed_text:
                return None
            
            # pyttsx3 plays directly, so we return a placeholder
            return "pyttsx3_direct_play"
            
        except Exception as e:
            self.logger.error(f"pyttsx3 error: {e}")
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
                result = self.speak(text)
                if result:
                    # Actually speak the text
                    self.engine.say(text)
                    self.engine.runAndWait()
                
                if callback:
                    callback(result)
                    
            except Exception as e:
                self.logger.error(f"Async pyttsx3 error: {e}")
                if callback:
                    callback(None)
        
        thread = threading.Thread(target=_speak_worker)
        thread.daemon = True
        thread.start()
    
    def speak_and_play(self, text: str) -> bool:
        """
        Convert text to speech and play it immediately
        
        Args:
            text: Text to convert to speech
            
        Returns:
            True if successful, False otherwise
        """
        try:
            processed_text = self.preprocess_text(text)
            if not processed_text:
                return False
            
            self.engine.say(processed_text)
            self.engine.runAndWait()
            return True
            
        except Exception as e:
            self.logger.error(f"Speak and play error: {e}")
            return False
    
    def get_available_voices(self) -> list:
        """
        Get list of available voices
        
        Returns:
            List of voice information
        """
        try:
            voices = self.engine.getProperty('voices')
            return [
                {
                    'id': voice.id,
                    'name': voice.name,
                    'languages': voice.languages
                }
                for voice in voices
            ]
        except Exception as e:
            self.logger.error(f"Error getting voices: {e}")
            return []
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Set specific voice
        
        Args:
            voice_id: Voice ID to use
            
        Returns:
            True if voice was set successfully, False otherwise
        """
        try:
            self.engine.setProperty('voice', voice_id)
            return True
        except Exception as e:
            self.logger.error(f"Error setting voice: {e}")
            return False
    
    def set_rate(self, rate: int) -> None:
        """
        Set speech rate
        
        Args:
            rate: Speech rate (words per minute)
        """
        try:
            self.engine.setProperty('rate', rate)
        except Exception as e:
            self.logger.error(f"Error setting rate: {e}")
    
    def set_volume(self, volume: float) -> None:
        """
        Set volume
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        try:
            self.engine.setProperty('volume', max(0.0, min(1.0, volume)))
        except Exception as e:
            self.logger.error(f"Error setting volume: {e}")
    
    def stop(self) -> None:
        """Stop current speech"""
        try:
            self.engine.stop()
        except Exception as e:
            self.logger.error(f"Error stopping speech: {e}")
    
    def cleanup(self) -> None:
        """Clean up TTS engine"""
        try:
            self.engine.stop()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
