"""
OSM Navigation Service - FREE OpenStreetMap Routing
No API key required - completely free to use
"""
import requests
import json
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class OSMNavigationService:
    """Service for navigation using free OpenStreetMap OSRM API"""
    
    def __init__(self):
        """
        Initialize the navigation service
        Uses FREE public OSRM server - no API key needed!
        """
        self.osrm_base_url = "https://router.project-osrm.org"
        self.current_route = None
        self.current_step_index = 0
        logger.info("Initialized OSM Navigation Service (FREE - no API key required)")
        
    def get_directions(self, start_location: Dict, end_location: Dict, 
                      profile: str = 'foot') -> Optional[Dict]:
        """
        Get turn-by-turn directions between two points using FREE OSRM API
        
        Args:
            start_location: Dict with 'lat' and 'lng' keys
            end_location: Dict with 'lat' and 'lng' keys
            profile: Transportation profile ('foot', 'bike', 'car')
            
        Returns:
            Route information with turn-by-turn instructions
        """
        try:
            # Map profile names
            profile_mapping = {
                'foot': 'foot',
                'foot-walking': 'foot',
                'walking': 'foot',
                'bike': 'bike',
                'cycling': 'bike',
                'car': 'car',
                'driving': 'car',
                'driving-car': 'car'
            }
            
            osrm_profile = profile_mapping.get(profile, 'foot')
            
            # Build OSRM URL
            start_coords = f"{start_location['lng']},{start_location['lat']}"
            end_coords = f"{end_location['lng']},{end_location['lat']}"
            
            url = f"{self.osrm_base_url}/route/v1/{osrm_profile}/{start_coords};{end_coords}"
            params = {
                'overview': 'full',
                'steps': 'true',
                'geometries': 'geojson',
                'annotations': 'true'
            }
            
            logger.info(f"Requesting OSRM route: {url}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') != 'Ok' or not data.get('routes'):
                logger.error(f"OSRM API error: {data}")
                return None
            
            route = data['routes'][0]
            self.current_route = route
            self.current_step_index = 0
            
            # Convert OSRM format to standardized format
            return self._convert_osrm_route(route, start_location, end_location)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OSRM API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting directions: {e}")
            return None
    
    def _convert_osrm_route(self, route: Dict, start: Dict, end: Dict) -> Dict:
        """Convert OSRM route format to standardized format"""
        try:
            # Extract route information
            distance = route.get('distance', 0)  # meters
            duration = route.get('duration', 0)  # seconds
            
            # Convert to steps
            steps = []
            if 'legs' in route and route['legs']:
                for leg in route['legs']:
                    if 'steps' in leg:
                        for step in leg['steps']:
                            steps.append({
                                'instruction': step.get('maneuver', {}).get('instruction', 'Continue'),
                                'distance': step.get('distance', 0),
                                'duration': step.get('duration', 0),
                                'location': {
                                    'lat': step.get('maneuver', {}).get('location', [0, 0])[1],
                                    'lng': step.get('maneuver', {}).get('location', [0, 0])[0]
                                }
                            })
            
            return {
                'distance': distance,
                'duration': duration,
                'steps': steps,
                'geometry': route.get('geometry', {}),
                'summary': f"Route: {distance/1000:.1f}km, {duration/60:.1f}min",
                'status': 'OK'
            }
            
        except Exception as e:
            logger.error(f"Error converting OSRM route: {e}")
            return None
    
    def get_current_instruction(self, current_location: Dict) -> Optional[Dict]:
        """
        Get current navigation instruction based on location
        
        Args:
            current_location: Dict with 'lat' and 'lng' keys
            
        Returns:
            Current instruction or None
        """
        if not self.current_route or not self.current_route.get('steps'):
            return None
        
        try:
            # Find closest step to current location
            min_distance = float('inf')
            closest_step = None
            closest_index = 0
            
            for i, step in enumerate(self.current_route['steps']):
                step_location = step.get('location', {})
                if step_location:
                    # Simple distance calculation
                    lat_diff = abs(step_location['lat'] - current_location['lat'])
                    lng_diff = abs(step_location['lng'] - current_location['lng'])
                    distance = (lat_diff ** 2 + lng_diff ** 2) ** 0.5
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_step = step
                        closest_index = i
            
            if closest_step:
                self.current_step_index = closest_index
                return {
                    'instruction': closest_step.get('instruction', 'Continue'),
                    'distance': closest_step.get('distance', 0),
                    'duration': closest_step.get('duration', 0),
                    'step_index': closest_index,
                    'total_steps': len(self.current_route['steps'])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current instruction: {e}")
            return None
    
    def get_route_summary(self) -> Optional[Dict]:
        """Get summary of current route"""
        if not self.current_route:
            return None
        
        return {
            'distance': self.current_route.get('distance', 0),
            'duration': self.current_route.get('duration', 0),
            'total_steps': len(self.current_route.get('steps', [])),
            'current_step': self.current_step_index
        }
    
    def clear_route(self):
        """Clear current route"""
        self.current_route = None
        self.current_step_index = 0
        logger.info("Route cleared")





