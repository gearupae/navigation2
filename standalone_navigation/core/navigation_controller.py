"""
Navigation Controller - Main controller that coordinates all services
"""
import logging
from typing import Dict, List, Optional, Any
from ..navigation.osm_service import OSMNavigationService
from ..navigation.google_places import GooglePlacesService
from ..navigation.location_utils import LocationUtils
from ..llm.base_llm import BaseLLM
from ..tts.base_tts import BaseTTS

logger = logging.getLogger(__name__)

class NavigationController:
    """Main controller that coordinates all navigation services"""
    
    def __init__(self, 
                 google_api_key: str = None,
                 llm: BaseLLM = None,
                 tts: BaseTTS = None):
        """
        Initialize navigation controller
        
        Args:
            google_api_key: Google Maps API key (optional)
            llm: LLM instance for vision analysis (optional)
            tts: TTS instance for audio output (optional)
        """
        self.logger = logger
        
        # Initialize services
        self.osm_service = OSMNavigationService()
        self.location_utils = LocationUtils()
        
        # Optional services
        self.google_places = None
        if google_api_key:
            self.google_places = GooglePlacesService(google_api_key)
        
        self.llm = llm
        self.tts = tts
        
        # State
        self.current_location = None
        self.current_route = None
        self.is_navigating = False
        self.vision_enabled = False
        
        self.logger.info("Navigation controller initialized")
    
    def set_location(self, lat: float, lng: float) -> bool:
        """
        Set current location
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            True if location was set successfully
        """
        if not self.location_utils.validate_coordinates(lat, lng):
            self.logger.error(f"Invalid coordinates: {lat}, {lng}")
            return False
        
        self.current_location = {'lat': lat, 'lng': lng}
        self.logger.info(f"Location set: {lat}, {lng}")
        return True
    
    def search_places(self, query: str, radius: int = 5000) -> List[Dict]:
        """
        Search for places
        
        Args:
            query: Search query
            radius: Search radius in meters
            
        Returns:
            List of place dictionaries
        """
        if not self.google_places:
            self.logger.error("Google Places service not available")
            return []
        
        return self.google_places.search_places(query, self.current_location, radius)
    
    def start_navigation(self, destination: Dict) -> bool:
        """
        Start navigation to destination
        
        Args:
            destination: Destination dict with 'lat' and 'lng' keys
            
        Returns:
            True if navigation started successfully
        """
        if not self.current_location:
            self.logger.error("Current location not set")
            return False
        
        try:
            # Get route from OSM
            route = self.osm_service.get_directions(
                self.current_location, 
                destination
            )
            
            if route:
                self.current_route = route
                self.is_navigating = True
                self.logger.info(f"Navigation started to {destination}")
                return True
            else:
                self.logger.error("Failed to get route")
                return False
                
        except Exception as e:
            self.logger.error(f"Navigation start error: {e}")
            return False
    
    def get_current_instruction(self) -> Optional[Dict]:
        """
        Get current navigation instruction
        
        Returns:
            Current instruction dictionary or None
        """
        if not self.is_navigating or not self.current_location:
            return None
        
        return self.osm_service.get_current_instruction(self.current_location)
    
    def analyze_image(self, image_data: bytes, prompt: str = None) -> Optional[Dict]:
        """
        Analyze image for navigation assistance
        
        Args:
            image_data: Image data as bytes
            prompt: Optional custom prompt
            
        Returns:
            Analysis results or None
        """
        if not self.llm:
            self.logger.error("LLM service not available")
            return None
        
        try:
            return self.llm.analyze_image(image_data, prompt)
        except Exception as e:
            self.logger.error(f"Image analysis error: {e}")
            return None
    
    def speak_instruction(self, text: str) -> bool:
        """
        Speak navigation instruction
        
        Args:
            text: Text to speak
            
        Returns:
            True if speech was successful
        """
        if not self.tts:
            self.logger.warning("TTS service not available")
            return False
        
        try:
            if hasattr(self.tts, 'speak_and_play'):
                return self.tts.speak_and_play(text)
            else:
                audio_path = self.tts.speak(text)
                return audio_path is not None
        except Exception as e:
            self.logger.error(f"TTS error: {e}")
            return False
    
    def get_unified_instruction(self, vision_analysis: Dict = None) -> Dict:
        """
        Get unified instruction combining navigation and vision
        
        Args:
            vision_analysis: Optional vision analysis results
            
        Returns:
            Unified instruction dictionary
        """
        # Get navigation instruction
        nav_instruction = self.get_current_instruction()
        
        # Determine context and priority
        context = "Route following"
        priority = "map"
        instruction = "Continue following your route"
        
        # Check if vision analysis is available and has obstacles
        if vision_analysis and vision_analysis.get('hazards'):
            hazards = vision_analysis.get('hazards', [])
            if len(hazards) > 0:
                context = "Obstacle avoidance"
                priority = "vision"
                
                # Get steering guidance
                steer = vision_analysis.get('suggested_heading', 'straight')
                
                # Get current route direction
                nav_direction = 'straight'
                if nav_instruction:
                    nav_text = nav_instruction.get('instruction', '')
                    nav_direction = self._extract_direction_from_instruction(nav_text)
                
                # Provide specific avoidance instruction
                if steer == 'left':
                    instruction = f"Move left to avoid obstacle, then continue {nav_direction}"
                elif steer == 'right':
                    instruction = f"Move right to avoid obstacle, then continue {nav_direction}"
                elif steer == 'slightly left':
                    instruction = f"Move slightly left to avoid obstacle, then continue {nav_direction}"
                elif steer == 'slightly right':
                    instruction = f"Move slightly right to avoid obstacle, then continue {nav_direction}"
                else:
                    # Default avoidance guidance
                    if nav_direction == 'left':
                        instruction = f"Move right to avoid obstacle, then continue {nav_direction}"
                    elif nav_direction == 'right':
                        instruction = f"Move left to avoid obstacle, then continue {nav_direction}"
                    else:
                        instruction = f"Move slightly left to avoid obstacle, then continue {nav_direction}"
        
        # Use navigation instruction if no obstacles
        elif nav_instruction:
            context = "Clear path - following route"
            priority = "map"
            
            distance = nav_instruction.get('distance', 0)
            steps_remaining = self.location_utils.meters_to_steps(distance)
            nav_text = nav_instruction.get('instruction', '')
            direction = self._extract_direction_from_instruction(nav_text)
            
            if steps_remaining > 0:
                instruction = f"Walk {steps_remaining} steps {direction}"
            else:
                instruction = self._make_route_instruction_brief(nav_text)
        
        return {
            'instruction': instruction,
            'context': context,
            'priority': priority,
            'distance': nav_instruction.get('distance', 0) if nav_instruction else 0,
            'duration': nav_instruction.get('duration', 0) if nav_instruction else 0,
            'vision_enabled': self.vision_enabled
        }
    
    def stop_navigation(self):
        """Stop current navigation"""
        self.is_navigating = False
        self.current_route = None
        self.osm_service.clear_route()
        self.logger.info("Navigation stopped")
    
    def get_route_summary(self) -> Optional[Dict]:
        """Get summary of current route"""
        if not self.is_navigating:
            return None
        
        return self.osm_service.get_route_summary()
    
    def _extract_direction_from_instruction(self, instruction: str) -> str:
        """Extract direction from navigation instruction"""
        instruction_lower = instruction.lower()
        
        if any(word in instruction_lower for word in ['left', 'turn left']):
            return 'left'
        elif any(word in instruction_lower for word in ['right', 'turn right']):
            return 'right'
        elif any(word in instruction_lower for word in ['straight', 'continue', 'ahead']):
            return 'straight'
        else:
            return 'straight'
    
    def _make_route_instruction_brief(self, instruction: str) -> str:
        """Make route instruction more brief and actionable"""
        # Remove common prefixes
        prefixes_to_remove = [
            'in 250 meters, ',
            'in 500 meters, ',
            'in 1 kilometer, ',
            'continue for ',
            'proceed for '
        ]
        
        brief = instruction.lower()
        for prefix in prefixes_to_remove:
            brief = brief.replace(prefix, '')
        
        # Capitalize first letter
        brief = brief.capitalize()
        
        return brief
    
    def set_llm(self, llm: BaseLLM):
        """Set LLM instance"""
        self.llm = llm
        self.logger.info("LLM service set")
    
    def set_tts(self, tts: BaseTTS):
        """Set TTS instance"""
        self.tts = tts
        self.logger.info("TTS service set")
    
    def enable_vision(self):
        """Enable vision analysis"""
        self.vision_enabled = True
        self.logger.info("Vision analysis enabled")
    
    def disable_vision(self):
        """Disable vision analysis"""
        self.vision_enabled = False
        self.logger.info("Vision analysis disabled")
    
    def get_status(self) -> Dict:
        """Get current system status"""
        return {
            'is_navigating': self.is_navigating,
            'current_location': self.current_location,
            'vision_enabled': self.vision_enabled,
            'has_google_places': self.google_places is not None,
            'has_llm': self.llm is not None,
            'has_tts': self.tts is not None,
            'route_summary': self.get_route_summary()
        }
