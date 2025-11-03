"""
Improved Text-to-Speech Module
Provides multiple TTS engine options with fallback support
"""
import logging
from enum import Enum
from typing import Optional
import os

logger = logging.getLogger(__name__)

class TTSEngine(Enum):
    """Available TTS engines"""
    GTTS = "gtts"           # Google TTS (online, high quality)
    PYTTSX3 = "pyttsx3"     # Offline TTS (system-based)
    ESPEAK = "espeak"       # Fast offline TTS

class ImprovedTTS:
    """Improved TTS engine with multiple backend support"""
    
    def __init__(self, engine: TTSEngine = TTSEngine.GTTS):
        """
        Initialize TTS engine
        
        Args:
            engine: Preferred TTS engine to use
        """
        self.engine_type = engine
        self.rate = 150
        self.volume = 0.9
        self.language = 'en'
        self.engine = None
        
        # Try to initialize the selected engine
        try:
            if engine == TTSEngine.GTTS:
                self._init_gtts()
            elif engine == TTSEngine.PYTTSX3:
                self._init_pyttsx3()
            elif engine == TTSEngine.ESPEAK:
                self._init_espeak()
            else:
                raise ValueError(f"Unknown TTS engine: {engine}")
                
            logger.info(f"TTS engine initialized: {engine.value}")
            
        except Exception as e:
            logger.error(f"Failed to initialize {engine.value}: {e}")
            # Try fallback to pyttsx3
            try:
                logger.info("Attempting fallback to pyttsx3...")
                self._init_pyttsx3()
                self.engine_type = TTSEngine.PYTTSX3
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                logger.warning("TTS will be disabled")
                self.engine = None
    
    def _init_gtts(self):
        """Initialize Google TTS"""
        try:
            from gtts import gTTS
            self.engine = "gtts"
            logger.info("Google TTS (gTTS) initialized")
        except ImportError:
            raise ImportError("gTTS not installed. Install with: pip install gtts")
    
    def _init_pyttsx3(self):
        """Initialize pyttsx3"""
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            if self.engine:
                self.engine.setProperty('rate', self.rate)
                self.engine.setProperty('volume', self.volume)
            logger.info("pyttsx3 initialized")
        except Exception as e:
            raise ImportError(f"pyttsx3 initialization failed: {e}")
    
    def _init_espeak(self):
        """Initialize espeak (command-line based)"""
        import subprocess
        try:
            # Check if espeak is available
            result = subprocess.run(['which', 'espeak'], 
                                    capture_output=True, 
                                    timeout=2)
            if result.returncode == 0:
                self.engine = "espeak"
                logger.info("espeak initialized")
            else:
                raise RuntimeError("espeak not found in PATH")
        except Exception as e:
            raise RuntimeError(f"espeak initialization failed: {e}")
    
    def set_settings(self, rate: int = None, volume: float = None, language: str = None):
        """
        Configure TTS settings
        
        Args:
            rate: Speech rate (words per minute)
            volume: Volume level (0.0 to 1.0)
            language: Language code (e.g., 'en', 'es')
        """
        if rate is not None:
            self.rate = rate
        if volume is not None:
            self.volume = volume
        if language is not None:
            self.language = language
        
        # Apply settings to pyttsx3 engine if available
        if self.engine_type == TTSEngine.PYTTSX3 and self.engine:
            try:
                self.engine.setProperty('rate', self.rate)
                self.engine.setProperty('volume', self.volume)
            except Exception as e:
                logger.warning(f"Failed to apply settings to pyttsx3: {e}")
    
    def speak(self, text: str, priority: str = 'normal') -> bool:
        """
        Speak the given text
        
        Args:
            text: Text to speak
            priority: Priority level ('high', 'normal', 'low')
            
        Returns:
            True if speech was successful, False otherwise
        """
        if not self.engine:
            logger.warning("TTS engine not available, skipping speech")
            return False
        
        try:
            if self.engine_type == TTSEngine.GTTS:
                return self._speak_gtts(text)
            elif self.engine_type == TTSEngine.PYTTSX3:
                return self._speak_pyttsx3(text)
            elif self.engine_type == TTSEngine.ESPEAK:
                return self._speak_espeak(text)
            else:
                logger.error(f"Unknown engine type: {self.engine_type}")
                return False
        except Exception as e:
            logger.error(f"Speech failed: {e}")
            return False
    
    def _speak_gtts(self, text: str) -> bool:
        """Speak using Google TTS"""
        try:
            from gtts import gTTS
            import tempfile
            import os
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_file = fp.name
            
            # Generate speech
            tts = gTTS(text=text, lang=self.language, slow=False)
            tts.save(temp_file)
            
            # Play the audio (using system player)
            try:
                # Try different audio players
                for player in ['mpg123', 'afplay', 'mpg321', 'play']:
                    import subprocess
                    result = subprocess.run(['which', player], 
                                            capture_output=True, 
                                            timeout=2)
                    if result.returncode == 0:
                        subprocess.run([player, temp_file], 
                                       capture_output=True, 
                                       timeout=30)
                        break
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
            
            return True
        except Exception as e:
            logger.error(f"gTTS speech failed: {e}")
            return False
    
    def _speak_pyttsx3(self, text: str) -> bool:
        """Speak using pyttsx3"""
        try:
            if self.engine:
                self.engine.say(text)
                self.engine.runAndWait()
                return True
            return False
        except Exception as e:
            logger.error(f"pyttsx3 speech failed: {e}")
            return False
    
    def _speak_espeak(self, text: str) -> bool:
        """Speak using espeak"""
        try:
            import subprocess
            # Use espeak command
            subprocess.run(['espeak', '-s', str(self.rate), 
                            '-a', str(int(self.volume * 200)),
                            '-v', self.language, text],
                           capture_output=True,
                           timeout=30)
            return True
        except Exception as e:
            logger.error(f"espeak speech failed: {e}")
            return False
    
    def get_engine_info(self) -> str:
        """
        Get information about the current TTS engine
        
        Returns:
            Engine information string
        """
        if not self.engine:
            return "TTS engine: None (disabled)"
        
        return f"TTS engine: {self.engine_type.value}, Rate: {self.rate}, Volume: {self.volume}, Language: {self.language}"
    
    def stop(self):
        """Stop any ongoing speech"""
        try:
            if self.engine_type == TTSEngine.PYTTSX3 and self.engine:
                self.engine.stop()
        except Exception as e:
            logger.warning(f"Failed to stop TTS: {e}")

