"""
Speech Service Module
Handles speech recognition and text-to-speech synthesis
"""
import speech_recognition as sr
import threading
import queue
import logging
from typing import Optional, Callable, Dict, Any
from config import Config
from .improved_tts import ImprovedTTS, TTSEngine

logger = logging.getLogger(__name__)

class SpeechService:
    """Service for speech recognition and text-to-speech"""
    
    def __init__(self):
        """Initialize the speech service"""
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.tts_engine = self._init_tts_engine()
        
        # Try to initialize microphone (optional for server environments)
        try:
            self.microphone = sr.Microphone()
            logger.info("Microphone initialized successfully")
        except Exception as e:
            logger.warning(f"Microphone not available (server environment): {str(e)}")
            logger.info("Speech recognition will be disabled, TTS will still work")
        
        # Speech recognition settings
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        
        # Threading for continuous listening
        self.listening = False
        self.listen_thread = None
        self.speech_queue = queue.Queue()
        
        # Callback for voice commands
        self.command_callback = None
        
        logger.info("Speech service initialized")
    
    def _init_tts_engine(self) -> ImprovedTTS:
        """
        Initialize improved text-to-speech engine
        
        Returns:
            Configured TTS engine
        """
        try:
            # Prefer higher-quality TTS
            preferred = TTSEngine.GTTS
            tts = ImprovedTTS(preferred)
            
            # Configure settings
            tts.set_settings(
                rate=Config.SPEECH_RATE,
                volume=Config.SPEECH_VOLUME,  # Keep requested volume
                language='en'
            )
            
            logger.info(f"TTS engine initialized: {tts.get_engine_info()}")
            return tts
            
        except Exception as e:
            logger.error(f"Error initializing improved TTS engine: {str(e)}")
            raise
    
    def speak(self, text: str, interrupt: bool = False, priority: str = "normal") -> None:
        """
        Convert text to speech using improved TTS
        
        Args:
            text: Text to speak
            interrupt: Whether to interrupt current speech
            priority: Priority level ("high", "normal", "low")
        """
        try:
            if self.tts_engine:
                self.tts_engine.speak(text, priority=priority, interrupt=interrupt)
            else:
                logger.warning(f"TTS engine not available - would speak: {text}")
            
        except Exception as e:
            logger.error(f"Error in text-to-speech: {str(e)}")
    
    def _speak_text(self, text: str) -> None:
        """
        Internal method to speak text (legacy - now uses improved TTS)
        
        Args:
            text: Text to speak
        """
        # This method is now handled by improved TTS
        if self.tts_engine:
            self.tts_engine.speak(text, priority="normal")
    
    def stop_speaking(self) -> None:
        """Stop current speech"""
        try:
            if self.tts_engine:
                self.tts_engine.stop_speaking()
        except Exception as e:
            logger.error(f"Error stopping speech: {str(e)}")
    
    def calibrate_microphone(self) -> bool:
        """
        Calibrate microphone for ambient noise
        
        Returns:
            True if calibration successful
        """
        try:
            if not self.microphone:
                logger.warning("Microphone not available - skipping calibration")
                self.speak("Microphone not available on this device.", priority="high")
                return False
                
            logger.info("Calibrating microphone for ambient noise...")
            self.speak("Please wait, calibrating microphone for ambient noise.", priority="high")
            
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            
            logger.info("Microphone calibration completed")
            self.speak("Microphone calibration completed.", priority="high")
            return True
            
        except Exception as e:
            logger.error(f"Error calibrating microphone: {str(e)}")
            self.speak("Error calibrating microphone.", priority="high")
            return False
    
    def listen_for_command(self, timeout: int = 5, phrase_time_limit: int = 10) -> Optional[str]:
        """
        Listen for a single voice command
        
        Args:
            timeout: Seconds to wait for speech to start
            phrase_time_limit: Maximum seconds for a phrase
            
        Returns:
            Recognized text or None
        """
        try:
            if not self.microphone:
                logger.warning("Microphone not available - cannot listen for commands")
                return None
                
            logger.info("Listening for command...")
            
            with self.microphone as source:
                # Listen for audio
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
            
            # Recognize speech using Google Speech Recognition
            text = self.recognizer.recognize_google(audio).lower()
            logger.info(f"Recognized: {text}")
            
            return text
            
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Error with speech recognition service: {str(e)}")
            return None
        except sr.WaitTimeoutError:
            logger.warning("Listening timeout - no speech detected")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in speech recognition: {str(e)}")
            return None
    
    def start_continuous_listening(self, callback: Callable[[str], None]) -> bool:
        """
        Start continuous listening for voice commands
        
        Args:
            callback: Function to call with recognized text
            
        Returns:
            True if started successfully
        """
        try:
            if not self.microphone:
                logger.warning("Microphone not available - speech recognition disabled")
                self.speak("Voice recognition not available on this device.", priority="high")
                return False
                
            if self.listening:
                logger.warning("Already listening")
                return False
            
            self.command_callback = callback
            self.listening = True
            
            # Start listening thread
            self.listen_thread = threading.Thread(target=self._continuous_listen)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            
            logger.info("Started continuous listening")
            self.speak("Voice navigation ready. Say your command.", priority="high")
            return True
            
        except Exception as e:
            logger.error(f"Error starting continuous listening: {str(e)}")
            return False
    
    def stop_continuous_listening(self) -> None:
        """Stop continuous listening"""
        try:
            self.listening = False
            if self.listen_thread:
                self.listen_thread.join(timeout=2)
            
            logger.info("Stopped continuous listening")
            self.speak("Voice navigation stopped.", priority="high")
            
        except Exception as e:
            logger.error(f"Error stopping continuous listening: {str(e)}")
    
    def _continuous_listen(self) -> None:
        """Internal method for continuous listening"""
        logger.info("Continuous listening thread started")
        
        while self.listening:
            try:
                # Listen for wake word or command
                command = self.listen_for_command(timeout=1, phrase_time_limit=5)
                
                if command and self.command_callback:
                    # Process command in main thread
                    self.command_callback(command)
                
            except Exception as e:
                logger.error(f"Error in continuous listening: {str(e)}")
                continue
        
        logger.info("Continuous listening thread ended")
    
    def process_voice_command(self, command: str) -> Dict[str, Any]:
        """
        Process and classify voice command
        
        Args:
            command: Voice command text
            
        Returns:
            Dict with command classification and parameters
        """
        try:
            command = command.lower().strip()
            
            # Navigation commands
            if any(phrase in command for phrase in ['go to', 'navigate to', 'take me to']):
                destination = self._extract_destination(command)
                return {
                    'type': 'navigate',
                    'destination': destination,
                    'raw_command': command
                }
            
            # Search commands
            elif any(phrase in command for phrase in ['find', 'search for', 'look for']):
                query = self._extract_search_query(command)
                return {
                    'type': 'search',
                    'query': query,
                    'raw_command': command
                }
            
            # Nearest location commands
            elif command.startswith('nearest'):
                return {
                    'type': 'search_nearby',
                    'query': command,
                    'raw_command': command
                }
            
            # Navigation control commands
            elif any(phrase in command for phrase in ['repeat', 'say again']):
                return {
                    'type': 'repeat_instruction',
                    'raw_command': command
                }
            
            elif any(phrase in command for phrase in ['next', 'continue']):
                return {
                    'type': 'next_instruction',
                    'raw_command': command
                }
            
            elif any(phrase in command for phrase in ['where am i', 'current location']):
                return {
                    'type': 'current_location',
                    'raw_command': command
                }
            
            elif any(phrase in command for phrase in ['save location', 'save this place']):
                return {
                    'type': 'save_location',
                    'raw_command': command
                }
            
            elif any(phrase in command for phrase in ['stop navigation', 'cancel route']):
                return {
                    'type': 'stop_navigation',
                    'raw_command': command
                }
            
            elif 'help' in command:
                return {
                    'type': 'help',
                    'raw_command': command
                }
            
            elif any(word in command for word in ['simulate', 'start simulation', 'auto move']):
                return {
                    'type': 'simulate',
                    'raw_command': command
                }
            
            elif any(word in command for word in ['move forward', 'advance', 'proceed', 'i moved']):
                return {
                    'type': 'manual_advance',
                    'raw_command': command
                }
            
            elif any(word in command for word in ['reroute', 're-route', 'recalculate', 'new route']):
                return {
                    'type': 'reroute',
                    'raw_command': command
                }
            
            else:
                return {
                    'type': 'unknown',
                    'raw_command': command
                }
                
        except Exception as e:
            logger.error(f"Error processing voice command: {str(e)}")
            return {
                'type': 'error',
                'raw_command': command,
                'error': str(e)
            }
    
    def _extract_destination(self, command: str) -> str:
        """
        Extract destination from navigation command
        
        Args:
            command: Voice command
            
        Returns:
            Destination string
        """
        # Remove common navigation phrases
        for phrase in ['go to', 'navigate to', 'take me to', 'i want to go to']:
            command = command.replace(phrase, '').strip()
        
        return command
    
    def _extract_search_query(self, command: str) -> str:
        """
        Extract search query from search command
        
        Args:
            command: Voice command
            
        Returns:
            Search query string
        """
        # Remove common search phrases
        for phrase in ['find', 'search for', 'look for']:
            command = command.replace(phrase, '').strip()
        
        return command
    
    def get_help_text(self) -> str:
        """
        Get help text for voice commands
        
        Returns:
            Help text for speech output
        """
        return """
        Here are the available voice commands:
        
        For navigation, say: "Go to" or "Navigate to" followed by the destination name.
        For example: "Go to Mzyad Mall" or "Navigate to nearest park"
        
        For searching, say: "Find" or "Search for" followed by what you're looking for.
        For example: "Find restaurants" or "Search for hospitals"
        
        For nearby places, say: "Nearest" followed by the place type.
        For example: "Nearest gas station" or "Nearest pharmacy"
        
        During navigation, you can say:
        "Repeat" to hear the current instruction again
        "Next" to get the next instruction
        "Where am I" to get your current location
        "Save location" to save the current destination
        "Stop navigation" to cancel the current route
        
        Say "Help" anytime to hear this message again.
        """