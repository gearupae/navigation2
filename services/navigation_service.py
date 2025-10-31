"""
Navigation Service using OpenRouteService API
Provides turn-by-turn directions and navigation instructions
"""
import openrouteservice as ors
import requests
import json
import logging
from typing import Dict, List, Optional, Tuple
from config import Config

logger = logging.getLogger(__name__)

class NavigationService:
    """Service for navigation and routing operations"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the navigation service
        
        Args:
            api_key: OpenRouteService API key
        """
        self.api_key = api_key or Config.OPENROUTESERVICE_API_KEY
        if not self.api_key:
            raise ValueError("OpenRouteService API key is required")
            
        self.client = ors.Client(key=self.api_key)
        self.current_route = None
        self.current_step_index = 0
        
    def get_directions(self, start_location: Dict, end_location: Dict, 
                      profile: str = 'foot-walking') -> Optional[Dict]:
        """
        Get turn-by-turn directions between two points
        
        Args:
            start_location: Dict with 'lat' and 'lng' keys
            end_location: Dict with 'lat' and 'lng' keys
            profile: Transportation profile (foot-walking, cycling, driving-car)
            
        Returns:
            Route information with turn-by-turn instructions
        """
        try:
            coordinates = [
                [start_location['lng'], start_location['lat']],
                [end_location['lng'], end_location['lat']]
            ]
            
            route = self.client.directions(
                coordinates=coordinates,
                profile=profile,
                format='geojson',
                instructions=True,
                language='en',
                units='m'
            )
            
            return self._process_route(route)
            
        except Exception as e:
            logger.error(f"Error getting directions: {str(e)}")
            return None
    
    def _process_route(self, route_data: Dict) -> Dict:
        """
        Process raw route data into structured format
        
        Args:
            route_data: Raw route data from OpenRouteService
            
        Returns:
            Processed route information
        """
        try:
            if not route_data.get('features'):
                return None
                
            feature = route_data['features'][0]
            properties = feature['properties']
            segments = properties.get('segments', [])
            
            if not segments:
                return None
            
            # Process turn-by-turn instructions
            instructions = []
            total_distance = 0
            total_duration = 0
            
            for segment in segments:
                steps = segment.get('steps', [])
                segment_distance = segment.get('distance', 0)
                segment_duration = segment.get('duration', 0)
                
                total_distance += segment_distance
                total_duration += segment_duration
                
                for step in steps:
                    instruction = self._format_instruction(step)
                    if instruction:
                        instructions.append(instruction)
            
            # Store current route
            self.current_route = {
                'instructions': instructions,
                'total_distance': total_distance,
                'total_duration': total_duration,
                'geometry': feature['geometry'],
                'waypoints': self._extract_waypoints(feature['geometry'])
            }
            
            self.current_step_index = 0
            
            return self.current_route
            
        except Exception as e:
            logger.error(f"Error processing route: {str(e)}")
            return None
    
    def _format_instruction(self, step: Dict) -> Optional[Dict]:
        """
        Format a single navigation instruction
        
        Args:
            step: Step data from OpenRouteService
            
        Returns:
            Formatted instruction dictionary
        """
        try:
            instruction_text = step.get('instruction', '')
            distance = step.get('distance', 0)
            duration = step.get('duration', 0)
            step_type = step.get('type', 0)
            
            # Convert instruction to more natural speech
            speech_instruction = self._convert_to_speech(instruction_text, distance)
            
            return {
                'instruction': instruction_text,
                'speech_instruction': speech_instruction,
                'distance': distance,
                'duration': duration,
                'type': step_type,
                'way_points': step.get('way_points', [])
            }
            
        except Exception as e:
            logger.error(f"Error formatting instruction: {str(e)}")
            return None
    
    def _convert_to_speech(self, instruction: str, distance: float) -> str:
        """
        Convert navigation instruction to natural speech
        
        Args:
            instruction: Original instruction text
            distance: Distance for this instruction
            
        Returns:
            Speech-friendly instruction text
        """
        try:
            # Format distance
            if distance < 50:
                distance_text = f"in {int(distance)} meters"
            elif distance < 100:
                distance_text = f"in about {int(distance/10)*10} meters"
            elif distance < 1000:
                distance_text = f"in {int(distance)} meters"
            else:
                km = distance / 1000
                distance_text = f"in {km:.1f} kilometers"
            
            # Clean up instruction text for speech
            speech_instruction = instruction.lower()
            
            # Replace common terms for better speech
            replacements = {
                'head': 'go',
                'continue': 'keep going',
                'slight': 'slightly',
                'sharp': 'sharply',
                'keep left': 'stay on the left',
                'keep right': 'stay on the right'
            }
            
            for old, new in replacements.items():
                speech_instruction = speech_instruction.replace(old, new)
            
            return f"{distance_text}, {speech_instruction}"
            
        except Exception as e:
            logger.error(f"Error converting to speech: {str(e)}")
            return instruction
    
    def _extract_waypoints(self, geometry: Dict) -> List[Dict]:
        """
        Extract waypoints from route geometry
        
        Args:
            geometry: Route geometry from OpenRouteService
            
        Returns:
            List of waypoint coordinates
        """
        try:
            if geometry['type'] != 'LineString':
                return []
            
            coordinates = geometry['coordinates']
            waypoints = []
            
            for coord in coordinates:
                waypoints.append({
                    'lng': coord[0],
                    'lat': coord[1]
                })
            
            return waypoints
            
        except Exception as e:
            logger.error(f"Error extracting waypoints: {str(e)}")
            return []
    
    def get_current_instruction(self) -> Optional[Dict]:
        """
        Get the current navigation instruction
        
        Returns:
            Current instruction dictionary or None
        """
        if not self.current_route or self.current_step_index >= len(self.current_route['instructions']):
            return None
        
        return self.current_route['instructions'][self.current_step_index]
    
    def get_next_instruction(self) -> Optional[Dict]:
        """
        Get the next navigation instruction
        
        Returns:
            Next instruction dictionary or None
        """
        if not self.current_route:
            return None
        
        next_index = self.current_step_index + 1
        if next_index >= len(self.current_route['instructions']):
            return None
        
        return self.current_route['instructions'][next_index]
    
    def advance_to_next_instruction(self) -> bool:
        """
        Advance to the next instruction
        
        Returns:
            True if advanced successfully, False if at end
        """
        if not self.current_route:
            return False
        
        if self.current_step_index < len(self.current_route['instructions']) - 1:
            self.current_step_index += 1
            return True
        
        return False
    
    def is_route_completed(self) -> bool:
        """
        Check if the current route is completed
        
        Returns:
            True if route is completed
        """
        if not self.current_route:
            return True
        
        return self.current_step_index >= len(self.current_route['instructions'])
    
    def get_route_summary(self) -> Optional[str]:
        """
        Get a summary of the current route for speech
        
        Returns:
            Route summary text
        """
        if not self.current_route:
            return None
        
        try:
            distance = self.current_route['total_distance']
            duration = self.current_route['total_duration']
            
            # Format distance
            if distance < 1000:
                distance_text = f"{int(distance)} meters"
            else:
                km = distance / 1000
                distance_text = f"{km:.1f} kilometers"
            
            # Format duration
            minutes = int(duration / 60)
            if minutes < 1:
                duration_text = "less than a minute"
            elif minutes == 1:
                duration_text = "1 minute"
            else:
                duration_text = f"{minutes} minutes"
            
            return f"Route is {distance_text} long and will take approximately {duration_text} to walk"
            
        except Exception as e:
            logger.error(f"Error getting route summary: {str(e)}")
            return "Route information available"
    
    def check_user_location(self, current_location: Dict) -> Dict:
        """
        Check user's current location against the route
        
        Args:
            current_location: Dict with 'lat' and 'lng' keys
            
        Returns:
            Dict with navigation status and next instruction
        """
        result = {
            'on_route': True,
            'distance_to_next': 0,
            'current_instruction': None,
            'next_instruction': None,
            'route_completed': False
        }
        
        try:
            if not self.current_route:
                result['on_route'] = False
                return result
            
            current_instruction = self.get_current_instruction()
            if not current_instruction:
                result['route_completed'] = True
                return result
            
            result['current_instruction'] = current_instruction
            result['next_instruction'] = self.get_next_instruction()
            
            # Calculate distance to next waypoint (simplified)
            # In a real implementation, you'd check against the actual route geometry
            if self.current_route.get('waypoints'):
                next_waypoint_index = min(self.current_step_index + 1, 
                                        len(self.current_route['waypoints']) - 1)
                next_waypoint = self.current_route['waypoints'][next_waypoint_index]
                
                from .location_service import LocationService
                location_service = LocationService()
                result['distance_to_next'] = location_service.calculate_distance(
                    current_location, next_waypoint
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking user location: {str(e)}")
            result['on_route'] = False
            return result
    
    def get_reroute_if_needed(self, current_location: Dict, destination: Dict) -> Optional[Dict]:
        """
        Get new route if user is off the current route
        
        Args:
            current_location: Current user location
            destination: Final destination
            
        Returns:
            New route if rerouting is needed, None otherwise
        """
        try:
            location_status = self.check_user_location(current_location)
            
            if not location_status['on_route'] or location_status['distance_to_next'] > 100:
                logger.info("User appears to be off route, recalculating...")
                return self.get_directions(current_location, destination)
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking for reroute: {str(e)}")
            return None