"""
Google Places API Service
Handles location searching using Google Places API
"""
import googlemaps
import logging
from typing import Dict, List, Optional
from config import Config

logger = logging.getLogger(__name__)

class PlacesService:
    """Service for Google Places API operations"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Places service
        
        Args:
            api_key: Google Maps API key
        """
        self.api_key = api_key or Config.GOOGLE_MAPS_API_KEY
        if not self.api_key:
            raise ValueError("Google Maps API key is required")
            
        self.client = googlemaps.Client(key=self.api_key)
        
    def search_places(self, query: str, location: Dict = None, radius: int = 5000) -> List[Dict]:
        """
        Search for places using text query
        
        Args:
            query: Search query (e.g., "Mzyad Mall", "nearest park")
            location: Dict with 'lat' and 'lng' for nearby search
            radius: Search radius in meters
            
        Returns:
            List of place dictionaries
        """
        try:
            # Handle "nearest" queries
            if query.lower().startswith('nearest'):
                return self._search_nearby_places(query, location, radius)
            else:
                return self._search_text_places(query, location, radius)
                
        except Exception as e:
            logger.error(f"Error searching places: {str(e)}")
            return []
    
    def _search_text_places(self, query: str, location: Dict = None, radius: int = 5000) -> List[Dict]:
        """
        Search places using text search
        
        Args:
            query: Search query
            location: Current location for ranking
            radius: Search radius in meters
            
        Returns:
            List of formatted place results
        """
        try:
            # Use text search for specific places
            places_result = self.client.places(
                query=query,
                location=(location['lat'], location['lng']) if location else None,
                radius=radius,
                language='en'
            )
            
            return self._format_places_results(places_result.get('results', []))
            
        except Exception as e:
            logger.error(f"Error in text places search: {str(e)}")
            return []
    
    def _search_nearby_places(self, query: str, location: Dict, radius: int = 5000) -> List[Dict]:
        """
        Search for nearby places by type
        
        Args:
            query: Search query containing place type
            location: Current location
            radius: Search radius in meters
            
        Returns:
            List of formatted place results
        """
        try:
            if not location:
                logger.error("Location required for nearby search")
                return []
            
            # Extract place type from query
            place_type = self._extract_place_type(query)
            
            # Use nearby search
            places_result = self.client.places_nearby(
                location=(location['lat'], location['lng']),
                radius=radius,
                type=place_type,
                language='en'
            )
            
            return self._format_places_results(places_result.get('results', []))
            
        except Exception as e:
            logger.error(f"Error in nearby places search: {str(e)}")
            return []
    
    def _extract_place_type(self, query: str) -> str:
        """
        Extract Google Places type from query
        
        Args:
            query: Search query
            
        Returns:
            Google Places type string
        """
        query_lower = query.lower()
        
        # Common mappings
        type_mappings = {
            'park': 'park',
            'restaurant': 'restaurant',
            'hospital': 'hospital',
            'pharmacy': 'pharmacy',
            'bank': 'bank',
            'atm': 'atm',
            'gas station': 'gas_station',
            'mall': 'shopping_mall',
            'store': 'store',
            'supermarket': 'supermarket',
            'school': 'school',
            'university': 'university',
            'mosque': 'mosque',
            'church': 'church',
            'temple': 'hindu_temple',
            'bus station': 'bus_station',
            'train station': 'train_station',
            'airport': 'airport'
        }
        
        for key, value in type_mappings.items():
            if key in query_lower:
                return value
        
        # Default to establishment
        return 'establishment'
    
    def _format_places_results(self, results: List[Dict]) -> List[Dict]:
        """
        Format Google Places results for the application
        
        Args:
            results: Raw Google Places API results
            
        Returns:
            List of formatted place dictionaries
        """
        formatted_results = []
        
        for place in results[:Config.MAX_SEARCH_RESULTS]:
            try:
                formatted_place = {
                    'place_id': place.get('place_id'),
                    'name': place.get('name'),
                    'address': place.get('formatted_address', place.get('vicinity')),
                    'location': {
                        'lat': place['geometry']['location']['lat'],
                        'lng': place['geometry']['location']['lng']
                    },
                    'rating': place.get('rating', 0),
                    'user_ratings_total': place.get('user_ratings_total', 0),
                    'types': place.get('types', []),
                    'opening_hours': self._format_opening_hours(place.get('opening_hours')),
                    'price_level': place.get('price_level'),
                    'business_status': place.get('business_status')
                }
                
                formatted_results.append(formatted_place)
                
            except Exception as e:
                logger.error(f"Error formatting place result: {str(e)}")
                continue
        
        return formatted_results
    
    def _format_opening_hours(self, opening_hours: Dict) -> Optional[Dict]:
        """
        Format opening hours information
        
        Args:
            opening_hours: Opening hours from Google Places API
            
        Returns:
            Formatted opening hours dict or None
        """
        if not opening_hours:
            return None
        
        return {
            'open_now': opening_hours.get('open_now', False),
            'weekday_text': opening_hours.get('weekday_text', [])
        }
    
    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """
        Get detailed information about a place
        
        Args:
            place_id: Google Places place_id
            
        Returns:
            Detailed place information or None
        """
        try:
            place_details = self.client.place(
                place_id=place_id,
                fields=['name', 'formatted_address', 'geometry', 'formatted_phone_number',
                       'website', 'rating', 'user_ratings_total', 'reviews', 'opening_hours']
            )
            
            result = place_details.get('result', {})
            
            return {
                'place_id': place_id,
                'name': result.get('name'),
                'address': result.get('formatted_address'),
                'location': {
                    'lat': result['geometry']['location']['lat'],
                    'lng': result['geometry']['location']['lng']
                },
                'phone': result.get('formatted_phone_number'),
                'website': result.get('website'),
                'rating': result.get('rating', 0),
                'user_ratings_total': result.get('user_ratings_total', 0),
                'opening_hours': self._format_opening_hours(result.get('opening_hours')),
                'reviews': result.get('reviews', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting place details: {str(e)}")
            return None
    
    def format_place_for_speech(self, place: Dict, include_distance: bool = False, 
                               current_location: Dict = None) -> str:
        """
        Format place information for speech output
        
        Args:
            place: Place dictionary
            include_distance: Whether to include distance information
            current_location: Current location for distance calculation
            
        Returns:
            Formatted text for speech
        """
        try:
            speech_text = f"{place['name']}"
            
            if place.get('address'):
                speech_text += f" located at {place['address']}"
            
            if place.get('rating') and place['rating'] > 0:
                speech_text += f" with a {place['rating']} star rating"
            
            if include_distance and current_location:
                from .location_service import LocationService
                location_service = LocationService()
                distance = location_service.calculate_distance(current_location, place['location'])
                formatted_distance = location_service.format_distance(distance)
                speech_text += f", {formatted_distance} away"
            
            if place.get('opening_hours', {}).get('open_now') is False:
                speech_text += ". Currently closed"
            elif place.get('opening_hours', {}).get('open_now') is True:
                speech_text += ". Currently open"
            
            return speech_text
            
        except Exception as e:
            logger.error(f"Error formatting place for speech: {str(e)}")
            return place.get('name', 'Unknown location')