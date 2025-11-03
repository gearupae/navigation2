"""
Location Utilities - GPS calculations and location helpers
"""
import math
from typing import Dict, List, Tuple, Optional

class LocationUtils:
    """Utility functions for location calculations"""
    
    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        
        Args:
            lat1, lng1: First point coordinates
            lat2, lng2: Second point coordinates
            
        Returns:
            Distance in meters
        """
        # Earth's radius in meters
        R = 6371000
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        # Calculate differences
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        # Haversine formula
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    @staticmethod
    def calculate_bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate bearing from point 1 to point 2
        
        Args:
            lat1, lng1: Starting point coordinates
            lat2, lng2: Destination point coordinates
            
        Returns:
            Bearing in degrees (0-360)
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        # Calculate bearing
        dlng = lng2_rad - lng1_rad
        
        y = math.sin(dlng) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlng))
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    @staticmethod
    def bearing_to_direction(bearing: float) -> str:
        """
        Convert bearing to compass direction
        
        Args:
            bearing: Bearing in degrees (0-360)
            
        Returns:
            Compass direction string
        """
        directions = [
            "North", "Northeast", "East", "Southeast",
            "South", "Southwest", "West", "Northwest"
        ]
        
        index = round(bearing / 45) % 8
        return directions[index]
    
    @staticmethod
    def is_within_radius(lat1: float, lng1: float, lat2: float, lng2: float, radius_meters: float) -> bool:
        """
        Check if two points are within specified radius
        
        Args:
            lat1, lng1: First point coordinates
            lat2, lng2: Second point coordinates
            radius_meters: Radius in meters
            
        Returns:
            True if within radius, False otherwise
        """
        distance = LocationUtils.calculate_distance(lat1, lng1, lat2, lng2)
        return distance <= radius_meters
    
    @staticmethod
    def format_distance(distance_meters: float) -> str:
        """
        Format distance in human-readable format
        
        Args:
            distance_meters: Distance in meters
            
        Returns:
            Formatted distance string
        """
        if distance_meters < 1000:
            return f"{int(distance_meters)}m"
        else:
            return f"{distance_meters/1000:.1f}km"
    
    @staticmethod
    def format_duration(duration_seconds: float) -> str:
        """
        Format duration in human-readable format
        
        Args:
            duration_seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if duration_seconds < 60:
            return f"{int(duration_seconds)}s"
        elif duration_seconds < 3600:
            minutes = int(duration_seconds / 60)
            return f"{minutes}min"
        else:
            hours = int(duration_seconds / 3600)
            minutes = int((duration_seconds % 3600) / 60)
            if minutes > 0:
                return f"{hours}h {minutes}min"
            else:
                return f"{hours}h"
    
    @staticmethod
    def meters_to_steps(distance_meters: float, step_length: float = 0.7) -> int:
        """
        Convert distance in meters to approximate steps
        
        Args:
            distance_meters: Distance in meters
            step_length: Average step length in meters (default 0.7m)
            
        Returns:
            Approximate number of steps
        """
        return int(distance_meters / step_length)
    
    @staticmethod
    def get_direction_instruction(bearing: float) -> str:
        """
        Get navigation instruction based on bearing
        
        Args:
            bearing: Bearing in degrees (0-360)
            
        Returns:
            Navigation instruction string
        """
        if bearing < 22.5 or bearing >= 337.5:
            return "Go straight ahead"
        elif bearing < 67.5:
            return "Turn slightly right"
        elif bearing < 112.5:
            return "Turn right"
        elif bearing < 157.5:
            return "Turn sharp right"
        elif bearing < 202.5:
            return "Turn around"
        elif bearing < 247.5:
            return "Turn sharp left"
        elif bearing < 292.5:
            return "Turn left"
        elif bearing < 337.5:
            return "Turn slightly left"
        else:
            return "Continue straight"
    
    @staticmethod
    def validate_coordinates(lat: float, lng: float) -> bool:
        """
        Validate if coordinates are within valid ranges
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            True if valid, False otherwise
        """
        return (-90 <= lat <= 90) and (-180 <= lng <= 180)
    
    @staticmethod
    def get_region_bounds(region: str) -> Optional[Dict]:
        """
        Get approximate bounds for common regions
        
        Args:
            region: Region name (e.g., 'UAE', 'Dubai', 'Abu Dhabi')
            
        Returns:
            Dictionary with 'north', 'south', 'east', 'west' bounds or None
        """
        bounds = {
            'UAE': {'north': 26.0, 'south': 22.5, 'east': 56.4, 'west': 51.0},
            'Dubai': {'north': 25.4, 'south': 24.8, 'east': 55.6, 'west': 54.8},
            'Abu Dhabi': {'north': 24.8, 'south': 23.5, 'east': 55.0, 'west': 53.5},
            'Sharjah': {'north': 25.5, 'south': 25.0, 'east': 55.8, 'west': 55.2}
        }
        
        return bounds.get(region)
    
    @staticmethod
    def is_in_region(lat: float, lng: float, region: str) -> bool:
        """
        Check if coordinates are within a specific region
        
        Args:
            lat: Latitude
            lng: Longitude
            region: Region name
            
        Returns:
            True if in region, False otherwise
        """
        bounds = LocationUtils.get_region_bounds(region)
        if not bounds:
            return False
        
        return (bounds['south'] <= lat <= bounds['north'] and 
                bounds['west'] <= lng <= bounds['east'])





