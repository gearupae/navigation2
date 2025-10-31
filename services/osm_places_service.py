"""
Places Service using FREE OpenStreetMap Nominatim API
No API key required - completely free to use
"""
import requests
import time
import logging
from typing import Dict, List, Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

logger = logging.getLogger(__name__)

class OSMPlacesService:
    """Service for place search using free OpenStreetMap Nominatim API"""
    
    def __init__(self):
        """
        Initialize the places service
        Uses FREE Nominatim - no API key needed!
        """
        # Initialize Nominatim geocoder with a user agent
        self.geocoder = Nominatim(user_agent="navigation_app_for_blind_v1.0")
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        logger.info("Initialized OSM Places Service (FREE - no API key required)")
        
    def search_places(self, query: str, location: Dict = None, radius: int = 5000) -> List[Dict]:
        """
        Search for places using FREE Nominatim API
        
        Args:
            query: Search query (e.g., "restaurant", "Mzyad Mall")
            location: Dict with 'lat' and 'lng' keys for nearby search
            radius: Search radius in meters (default: 5000m = 5km)
            
        Returns:
            List of place dictionaries
        """
        try:
            params = {
                'q': query,
                'format': 'json',
                'addressdetails': 1,
                'limit': 10,
                'extratags': 1
            }
            
            # If location is provided, search nearby
            if location:
                params['lat'] = location['lat']
                params['lon'] = location['lng']
                # Convert radius to viewbox (approximate)
                params['bounded'] = 1
            
            logger.info(f"Searching Nominatim for: {query}")
            
            # Be polite to Nominatim but keep it responsive
            time.sleep(0.25)
            
            response = requests.get(
                self.nominatim_url,
                params=params,
                headers={'User-Agent': 'navigation_app_for_blind_v1.0'},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.info(f"No results found for: {query}")
                
                # Try multiple fallback strategies
                fallback_queries = []
                
                if location:
                    # Strategy 1: Add UAE city context
                    fallback_queries.extend([
                        f"{query} Abu Dhabi",
                        f"{query} Dubai", 
                        f"{query} UAE",
                        f"{query} mall",  # Many searches are for malls
                        f"{query} shopping"
                    ])
                else:
                    # Strategy 2: Generic improvements
                    fallback_queries.extend([
                        f"{query} mall",
                        f"{query} shopping center",
                        f"{query} UAE"
                    ])
                
                # Try each fallback query
                for fallback_query in fallback_queries:
                    logger.info(f"Retrying Nominatim with fallback: {fallback_query}")
                    time.sleep(0.5)
                    try:
                        response = requests.get(
                            self.nominatim_url,
                            params={**params, 'q': fallback_query},
                            headers={'User-Agent': 'navigation_app_for_blind_v1.0'},
                            timeout=10
                        )
                        response.raise_for_status()
                        data = response.json()
                        
                        if data:
                            logger.info(f"Found results with fallback: {fallback_query}")
                            break
                    except Exception as e:
                        logger.debug(f"Fallback query '{fallback_query}' failed: {str(e)}")
                        continue
                
                if not data:
                    logger.warning(f"No results found even with fallback strategies for: {query}")
                    return []
            
            # Process results
            places = []
            for item in data[:5]:  # Limit to top 5 results
                place = self._process_place(item, location)
                if place:
                    places.append(place)
            
            logger.info(f"Found {len(places)} places for: {query}")
            return places
            
        except requests.RequestException as e:
            logger.error(f"Error requesting from Nominatim: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error searching places: {str(e)}")
            return []
    
    def _process_place(self, item: Dict, user_location: Dict = None) -> Optional[Dict]:
        """
        Process a Nominatim result into our place format
        
        Args:
            item: Raw Nominatim result
            user_location: User's current location for distance calculation
            
        Returns:
            Processed place dictionary
        """
        try:
            lat = float(item.get('lat', 0))
            lon = float(item.get('lon', 0))
            
            # Extract place name
            name = item.get('display_name', '').split(',')[0]
            if not name:
                name = item.get('name', 'Unknown place')
            
            # Build address
            address_parts = []
            address_data = item.get('address', {})
            
            # Add relevant address components
            for key in ['road', 'suburb', 'city', 'state', 'country']:
                if key in address_data and address_data[key]:
                    address_parts.append(address_data[key])
            
            address = ', '.join(address_parts) if address_parts else item.get('display_name', '')
            
            # Calculate distance if user location provided (in kilometers)
            distance_km = None
            distance_meters = None
            if user_location:
                distance_km = self._calculate_distance(
                    user_location['lat'], user_location['lng'],
                    lat, lon
                )
                try:
                    distance_meters = int(distance_km * 1000)
                except Exception:
                    distance_meters = None
            
            # Determine place type
            place_type = item.get('type', 'place')
            osm_type = item.get('class', '')
            
            place = {
                'name': name,
                'display_name': item.get('display_name', name),
                'address': address,
                'location': {'lat': lat, 'lng': lon},
                'place_id': item.get('place_id', item.get('osm_id', 'unknown')),
                'types': [osm_type, place_type],
                'rating': None,  # Nominatim doesn't provide ratings
                'distance': distance_km,
                'distance_meters': distance_meters
            }
            
            return place
            
        except Exception as e:
            logger.error(f"Error processing place: {str(e)}")
            return None
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        
        Returns:
            Distance in kilometers
        """
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        
        return round(distance, 2)
    
    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """
        Get detailed information about a place
        
        Args:
            place_id: Nominatim place ID
            
        Returns:
            Detailed place information
        """
        try:
            url = f"https://nominatim.openstreetmap.org/details"
            params = {
                'place_id': place_id,
                'format': 'json'
            }
            
            time.sleep(1)  # Respect rate limit
            
            response = requests.get(
                url,
                params=params,
                headers={'User-Agent': 'navigation_app_for_blind_v1.0'},
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting place details: {str(e)}")
            return None
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Convert coordinates to address
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Address string
        """
        try:
            time.sleep(0.25)  # Polite delay
            
            location = self.geocoder.reverse(f"{latitude}, {longitude}", language='en')
            
            if location:
                return location.address
            
            return None
            
        except GeocoderTimedOut:
            logger.error("Geocoder timed out")
            return None
        except Exception as e:
            logger.error(f"Error reverse geocoding: {str(e)}")
            return None
    
    def format_place_for_speech(self, place: Dict, include_distance: bool = True, 
                                current_location: Dict = None) -> str:
        """
        Format place information for speech output
        
        Args:
            place: Place dictionary
            include_distance: Whether to include distance
            current_location: Current location for distance calculation
            
        Returns:
            Speech-friendly place description
        """
        name = place.get('name', 'Unknown place')
        address = place.get('address', '')
        distance = place.get('distance')
        
        # Build speech text
        speech_parts = [name]
        
        if address:
            # Simplify address for speech - take first 2 parts
            address_parts = address.split(',')[:2]
            speech_parts.append(f"at {', '.join(address_parts)}")
        
        if include_distance and distance:
            if distance < 1:
                speech_parts.append(f"{int(distance * 1000)} meters away")
            else:
                speech_parts.append(f"{distance} kilometers away")
        
        return ', '.join(speech_parts)
