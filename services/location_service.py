"""
Location Service Module
Handles location detection, geocoding, and location-based operations
"""
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
import logging

logger = logging.getLogger(__name__)

class LocationService:
    """Service for handling location operations"""
    
    def __init__(self):
        """Initialize the location service"""
        self.geolocator = Nominatim(user_agent="blind-navigation-app")
        self.current_location = None
        
    def set_current_location(self, latitude: float, longitude: float) -> bool:
        """
        Set the current location coordinates
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            bool: True if location was set successfully
        """
        try:
            self.current_location = {
                'lat': float(latitude),
                'lng': float(longitude)
            }
            logger.info(f"Current location set to: {latitude}, {longitude}")
            return True
        except Exception as e:
            logger.error(f"Error setting current location: {str(e)}")
            return False
    
    def get_current_location(self) -> Optional[Dict]:
        """
        Get the current location
        
        Returns:
            Dict with lat/lng or None if not set
        """
        return self.current_location
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Convert coordinates to address
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Address string or None if failed
        """
        try:
            location = self.geolocator.reverse((latitude, longitude), timeout=10)
            if location:
                return location.address
            return None
        except Exception as e:
            logger.error(f"Error in reverse geocoding: {str(e)}")
            return None
    
    def geocode_address(self, address: str) -> Optional[Dict]:
        """
        Convert address to coordinates
        
        Args:
            address: Address string to geocode
            
        Returns:
            Dict with lat/lng or None if failed
        """
        try:
            location = self.geolocator.geocode(address, timeout=10)
            if location:
                return {
                    'lat': location.latitude,
                    'lng': location.longitude,
                    'address': location.address
                }
            return None
        except Exception as e:
            logger.error(f"Error in geocoding: {str(e)}")
            return None
    
    def calculate_distance(self, point1: Dict, point2: Dict) -> float:
        """
        Calculate distance between two points
        
        Args:
            point1: Dict with 'lat' and 'lng' keys
            point2: Dict with 'lat' and 'lng' keys
            
        Returns:
            Distance in meters
        """
        try:
            coord1 = (point1['lat'], point1['lng'])
            coord2 = (point2['lat'], point2['lng'])
            distance = geodesic(coord1, coord2).meters
            return distance
        except Exception as e:
            logger.error(f"Error calculating distance: {str(e)}")
            return 0.0
    
    def calculate_bearing(self, point1: Dict, point2: Dict) -> float:
        """
        Calculate bearing between two points
        
        Args:
            point1: Starting point with 'lat' and 'lng' keys
            point2: End point with 'lat' and 'lng' keys
            
        Returns:
            Bearing in degrees
        """
        try:
            import math
            
            lat1 = math.radians(point1['lat'])
            lat2 = math.radians(point2['lat'])
            lng_diff = math.radians(point2['lng'] - point1['lng'])
            
            y = math.sin(lng_diff) * math.cos(lat2)
            x = (math.cos(lat1) * math.sin(lat2) - 
                 math.sin(lat1) * math.cos(lat2) * math.cos(lng_diff))
            
            bearing = math.atan2(y, x)
            bearing = math.degrees(bearing)
            bearing = (bearing + 360) % 360
            
            return bearing
        except Exception as e:
            logger.error(f"Error calculating bearing: {str(e)}")
            return 0.0
    
    def get_direction_description(self, bearing: float) -> str:
        """
        Convert bearing to direction description
        
        Args:
            bearing: Bearing in degrees
            
        Returns:
            Direction description string
        """
        directions = [
            "North", "Northeast", "East", "Southeast",
            "South", "Southwest", "West", "Northwest"
        ]
        
        index = round(bearing / 45) % 8
        return directions[index]
    
    def is_location_nearby(self, target_location: Dict, threshold_meters: float = 50) -> bool:
        """
        Check if a location is nearby the current location
        
        Args:
            target_location: Dict with 'lat' and 'lng' keys
            threshold_meters: Distance threshold in meters
            
        Returns:
            True if location is nearby
        """
        if not self.current_location:
            return False
        
        distance = self.calculate_distance(self.current_location, target_location)
        return distance <= threshold_meters
    
    def format_distance(self, distance_meters: float) -> str:
        """
        Format distance for speech output
        
        Args:
            distance_meters: Distance in meters
            
        Returns:
            Formatted distance string
        """
        if distance_meters < 100:
            return f"{int(distance_meters)} meters"
        elif distance_meters < 1000:
            return f"{int(distance_meters)} meters"
        else:
            km = distance_meters / 1000
            return f"{km:.1f} kilometers"