"""
Navigation Service using FREE OpenStreetMap OSRM API
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
            
            # OSRM uses format: longitude,latitude
            start_coord = f"{start_location['lng']},{start_location['lat']}"
            end_coord = f"{end_location['lng']},{end_location['lat']}"
            
            # Build OSRM API URL
            url = f"{self.osrm_base_url}/route/v1/{osrm_profile}/{start_coord};{end_coord}"
            
            params = {
                'overview': 'full',
                'steps': 'true',
                'geometries': 'geojson',
                'annotations': 'true'
            }
            
            logger.info(f"🚶/🚗 ROUTING MODE: {osrm_profile.upper()} (requested: {profile})")
            logger.info(f"📍 OSRM URL: {url}")
            logger.info(f"📍 From: [{start_location['lat']}, {start_location['lng']}] To: [{end_location['lat']}, {end_location['lng']}]")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') != 'Ok':
                logger.error(f"OSRM returned error: {data.get('message')}")
                return None
            
            # Log route stats for debugging
            if data.get('routes'):
                route = data['routes'][0]
                distance_km = route.get('distance', 0) / 1000
                duration_min = route.get('duration', 0) / 60
                logger.info(f"✅ Route calculated: {distance_km:.2f} km, {duration_min:.1f} minutes using {osrm_profile.upper()} profile")
            
            return self._process_route(data)
            
        except requests.RequestException as e:
            logger.error(f"Error requesting directions from OSRM: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error getting directions: {str(e)}")
            return None
    
    def _process_route(self, route_data: Dict) -> Dict:
        """
        Process raw OSRM route data into structured format
        
        Args:
            route_data: Raw route data from OSRM
            
        Returns:
            Processed route information
        """
        try:
            if not route_data.get('routes'):
                return None
                
            route = route_data['routes'][0]
            legs = route.get('legs', [])
            
            if not legs:
                return None
            
            # Process turn-by-turn instructions
            instructions = []
            total_distance = route.get('distance', 0)  # in meters
            total_duration = route.get('duration', 0)  # in seconds
            
            for leg in legs:
                steps = leg.get('steps', [])
                
                for step in steps:
                    instruction = self._format_instruction(step)
                    if instruction:
                        instructions.append(instruction)
            
            # Store current route
            self.current_route = {
                'engine': 'osrm',
                'instructions': instructions,
                'total_distance': total_distance,
                'total_duration': total_duration,
                'geometry': route.get('geometry'),
                'waypoints': route_data.get('waypoints', [])
            }
            
            self.current_step_index = 0
            
            logger.info(f"Route processed: {len(instructions)} instructions, "
                       f"{total_distance:.0f}m, {total_duration:.0f}s")
            
            return self.current_route
            
        except Exception as e:
            logger.error(f"Error processing route: {str(e)}")
            return None
    
    def _format_instruction(self, step: Dict) -> Optional[Dict]:
        """
        Format a single navigation instruction from OSRM step
        
        Args:
            step: Step data from OSRM
            
        Returns:
            Formatted instruction dictionary
        """
        try:
            # OSRM provides maneuver information
            maneuver = step.get('maneuver', {})
            maneuver_type = maneuver.get('type', 'continue')
            modifier = maneuver.get('modifier', '')
            exit_no = maneuver.get('exit')
            
            distance = step.get('distance', 0)  # in meters
            duration = step.get('duration', 0)  # in seconds
            
            # Preserve Arabic street names - check multiple name fields
            name = step.get('name', '')
            if not name:
                # Try alternative name fields that might contain Arabic text
                name = step.get('ref', '') or step.get('destinations', '') or 'the road'
            
            # Build instruction text
            instruction_text = self._build_instruction_text(maneuver_type, modifier, name, exit_no)
            
            # Convert to spoken form
            speech_instruction = self._convert_to_speech(
                instruction_text, distance, maneuver_type, modifier, name, exit_no
            )
            
            loc = maneuver.get('location', None)
            man_loc = None
            if isinstance(loc, list) and len(loc) == 2:
                # OSRM: [lon, lat]
                man_loc = {'lng': float(loc[0]), 'lat': float(loc[1])}
            
            return {
                'instruction': instruction_text,
                'speech_instruction': speech_instruction,
                'distance': distance,
                'duration': duration,
                'type': maneuver_type,
                'modifier': modifier,
                'name': name,
                'maneuver_location': man_loc
            }
            
        except Exception as e:
            logger.error(f"Error formatting instruction: {str(e)}")
            return None
    
    def _build_instruction_text(self, maneuver_type: str, modifier: str, road_name: str, exit_no: Optional[int] = None) -> str:
        """
        Build a calm, concise instruction from OSRM maneuver data.
        """
        # Ensure road_name is properly encoded and not empty
        if not road_name or str(road_name).strip() == '':
            road_name = 'the road'
        else:
            road_name = str(road_name).strip()
        
        def onto():
            return '' if road_name == 'the road' else f" onto {road_name}"
        
        mt = (maneuver_type or '').lower()
        mod = (modifier or '').lower()
        
        if mt == 'depart':
            return f"Start on {road_name}" if road_name != 'the road' else "Start and go straight"
        if mt == 'arrive':
            side = ' on the left' if mod == 'left' else (' on the right' if mod == 'right' else '')
            return f"You have arrived{side}"
        if mt in ('turn', 'end of road'):
            if 'slight' in mod:
                dirw = 'slightly left' if 'left' in mod else 'slightly right'
                return f"Turn {dirw}{onto()}"
            if 'sharp' in mod:
                dirw = 'sharply left' if 'left' in mod else 'sharply right'
                return f"Turn {dirw}{onto()}"
            if mod in ('left', 'right'):
                return f"Turn {mod}{onto()}"
            return f"Turn{onto()}"
        if mt in ('continue', 'new name', 'notification'):
            return f"Continue straight{onto()}"
        if mt == 'fork':
            if mod in ('left', 'right'):
                return f"Keep {mod}{onto()}"
            return f"Keep to the main path{onto()}"
        if mt == 'merge':
            if mod in ('left', 'right'):
                return f"Merge {mod}{onto()}"
            return f"Merge{onto()}"
        if mt == 'roundabout':
            if exit_no:
                def ordinal(n:int):
                    return f"{n}{'th' if 11<=n%100<=13 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th')}"
                return f"At the roundabout, take the {ordinal(int(exit_no))} exit{onto()}"
            if mod:
                return f"At the roundabout, go {mod}{onto()}"
            return f"At the roundabout, proceed straight{onto()}"
        if mt == 'u-turn':
            return "Make a U-turn and continue"
        
        # Fallback
        return f"Continue{onto()}"
    
    def _convert_to_speech(self, instruction_text: str, distance: float, maneuver_type: str, modifier: str, road_name: str, exit_no: Optional[int]) -> str:
        """
        Build calm, concise spoken instruction with distance phrasing.
        """
        try:
            def round_to(n, step):
                import math
                return int(step * round(float(n)/step))
            d = float(distance or 0)
            if d < 12:
                prefix = "Now,"
            elif d < 40:
                prefix = f"In {round_to(d, 5)} meters,"
            elif d < 150:
                prefix = f"In {round_to(d, 10)} meters,"
            elif d < 1000:
                prefix = f"In {round_to(d, 25)} meters,"
            else:
                km = d / 1000.0
                prefix = f"In {km:.1f} kilometers,"
            
            mt = (maneuver_type or '').lower()
            spoken = instruction_text.strip()
            # Arrival should not have a distance prefix
            if mt == 'arrive':
                return spoken
            return f"{prefix} {spoken}"
        except Exception as e:
            logger.error(f"Error converting to speech: {str(e)}")
            return instruction_text
    
    def get_route_summary(self, route_data: Dict = None) -> str:
        """
        Get a summary of the route
        
        Args:
            route_data: Route data (uses current_route if not provided)
            
        Returns:
            Summary string
        """
        try:
            route = route_data or self.current_route
            
            if not route:
                return "No route available"
            
            distance = route.get('total_distance', 0)
            duration = route.get('total_duration', 0)
            
            # Format distance
            if distance < 1000:
                distance_str = f"{int(distance)} meters"
            else:
                distance_str = f"{distance/1000:.1f} kilometers"
            
            # Format duration
            minutes = int(duration / 60)
            if minutes < 60:
                duration_str = f"{minutes} minutes"
            else:
                hours = minutes // 60
                mins = minutes % 60
                duration_str = f"{hours} hour{'s' if hours > 1 else ''} and {mins} minutes"
            
            return f"The route is {distance_str} and will take approximately {duration_str}"
            
        except Exception as e:
            logger.error(f"Error getting route summary: {str(e)}")
            return "Route information not available"
    
    def get_current_instruction(self, route_data: Dict = None, current_location: Dict = None) -> Dict:
        """
        Get the current navigation instruction
        
        Args:
            route_data: Route data (uses current_route if not provided)
            current_location: Current location (optional)
            
        Returns:
            Current instruction dictionary
        """
        try:
            route = route_data or self.current_route
            
            if not route or not route.get('instructions'):
                return None
            
            instructions = route['instructions']
            
            if self.current_step_index >= len(instructions):
                return None
            
            instruction = instructions[self.current_step_index]
            
            # Add progress information to the instruction
            if instruction:
                progress = self.calculate_progress(route, current_location)
                instruction['progress'] = progress
            
            return instruction
            
        except Exception as e:
            logger.error(f"Error getting current instruction: {str(e)}")
            return None
    
    def advance_to_next_instruction(self) -> bool:
        """
        Advance to the next instruction
        
        Returns:
            True if there's a next instruction, False if route is complete
        """
        if not self.current_route or not self.current_route.get('instructions'):
            return False
        
        self.current_step_index += 1
        
        if self.current_step_index >= len(self.current_route['instructions']):
            logger.info("Route completed - no more instructions")
            return False
        
        logger.info(f"Advanced to instruction {self.current_step_index}")
        return True
    
    def calculate_progress(self, route_data: Dict = None, current_location: Dict = None) -> Dict:
        """
        Calculate navigation progress
        
        Args:
            route_data: Route data (uses current_route if not provided)
            current_location: Current location
            
        Returns:
            Progress information
        """
        try:
            route = route_data or self.current_route
            
            if not route or not route.get('instructions'):
                return {}
            
            instructions = route['instructions']
            total_steps = len(instructions)
            
            # Calculate remaining distance and time
            remaining_distance = sum(
                step['distance'] 
                for step in instructions[self.current_step_index:]
            )
            
            remaining_duration = sum(
                step['duration'] 
                for step in instructions[self.current_step_index:]
            )
            
            # Calculate progress percentage
            total_distance = route.get('total_distance', 1)
            progress_percentage = int(((total_distance - remaining_distance) / total_distance) * 100)
            
            # Format remaining values
            if remaining_distance < 1000:
                distance_str = f"{int(remaining_distance)} meters"
            else:
                distance_str = f"{remaining_distance/1000:.1f} km"
            
            minutes = int(remaining_duration / 60)
            time_str = f"{minutes} min" if minutes > 0 else "less than 1 min"
            
            return {
                'distance_remaining': distance_str,
                'time_remaining': time_str,
                'progress_percentage': progress_percentage,
                'current_step': self.current_step_index + 1,
                'total_steps': total_steps
            }
            
        except Exception as e:
            logger.error(f"Error calculating progress: {str(e)}")
            return {}
