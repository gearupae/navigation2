"""
Google Places Service - Place Search with Location Prioritization
"""
from typing import Dict, List, Optional
import logging
import googlemaps
from datetime import datetime

logger = logging.getLogger(__name__)

class GooglePlacesService:
    """Service for searching places using Google Maps Places API"""
    
    def __init__(self, api_key: str):
        """
        Initialize Google Places service
        
        Args:
            api_key: Google Maps API key
        """
        self.client = googlemaps.Client(key=api_key)
        logger.info("Initialized Google Places Service")
    
    def _is_in_uae_region(self, location: Dict) -> bool:
        """Check if location is in UAE region (approximate coordinates)"""
        if not location:
            return False
        
        lat, lng = location.get('lat', 0), location.get('lng', 0)
        
        # UAE approximate boundaries
        # Latitude: 22.5 to 26.0
        # Longitude: 51.0 to 56.4
        return (22.5 <= lat <= 26.0) and (51.0 <= lng <= 56.4)

    def search_places(self, query: str, location: Optional[Dict] = None, radius: int = 5000) -> List[Dict]:
        """
        Search for places with location prioritization
        
        Args:
            query: Search query
            location: Current location dict with 'lat' and 'lng'
            radius: Search radius in meters
            
        Returns:
            List of place dictionaries
        """
        try:
            all_places = []
            
            # Strategy 1: If we have location, prioritize nearby search first
            if location:
                try:
                    # First try nearby search with keyword
                    resp_nearby = self.client.places_nearby(location=(location['lat'], location['lng']),
                                                          radius=radius,
                                                          keyword=query)
                    nearby_places = resp_nearby.get('results', [])
                    logger.info(f"Nearby search found {len(nearby_places)} results for '{query}'")
                    all_places.extend(nearby_places)
                    
                    # If nearby search didn't find enough results, try text search with location bias
                    if len(nearby_places) < 5:
                        try:
                            resp_text = self.client.places(query=query, location=(location['lat'], location['lng']), radius=radius*2)
                            text_places = resp_text.get('results', [])
                            logger.info(f"Location-biased text search found {len(text_places)} results for '{query}'")
                            
                            # Add text places that aren't already in nearby results
                            existing_place_ids = {p.get('place_id') for p in all_places}
                            for place in text_places:
                                if place.get('place_id') not in existing_place_ids:
                                    all_places.append(place)
                        except Exception as e:
                            logger.warning(f"Location-biased text search failed: {e}")
                    
                    # Strategy 2: Try with UAE context if we're in UAE region
                    if len(all_places) < 3 and self._is_in_uae_region(location):
                        try:
                            uae_queries = [
                                f"{query} UAE",
                                f"{query} Dubai",
                                f"{query} Abu Dhabi",
                                f"{query} Sharjah"
                            ]
                            for uae_query in uae_queries:
                                resp_uae = self.client.places(query=uae_query, location=(location['lat'], location['lng']), radius=100000)
                                uae_places = resp_uae.get('results', [])
                                logger.info(f"UAE context search found {len(uae_places)} results for '{uae_query}'")
                                
                                # Add UAE places that aren't already in results
                                existing_place_ids = {p.get('place_id') for p in all_places}
                                for place in uae_places:
                                    if place.get('place_id') not in existing_place_ids:
                                        all_places.append(place)
                                
                                if len(all_places) >= 5:
                                    break
                        except Exception as e:
                            logger.warning(f"UAE context search failed: {e}")
                except Exception as e:
                    logger.warning(f"Nearby search failed: {e}")
            
            # Strategy 3: If no location or still no results, try global search but filter by distance
            if len(all_places) == 0:
                try:
                    resp_text = self.client.places(query=query)
                    text_places = resp_text.get('results', [])
                    logger.info(f"Global text search found {len(text_places)} results for '{query}'")
                    all_places.extend(text_places)
                except Exception as e:
                    logger.warning(f"Global text search failed: {e}")
            
            # Strategy 4: If still no results, try with location context
            if len(all_places) == 0 and location:
                try:
                    context_query = f"{query} near {location['lat']:.2f},{location['lng']:.2f}"
                    resp_context = self.client.places(query=context_query)
                    context_places = resp_context.get('results', [])
                    logger.info(f"Context search found {len(context_places)} results for '{context_query}'")
                    all_places.extend(context_places)
                except Exception as e:
                    logger.warning(f"Context search failed: {e}")
            
            # Filter and sort results by distance if we have location
            if location and len(all_places) > 0:
                def calculate_distance(place):
                    place_loc = place.get('geometry', {}).get('location', {})
                    if not place_loc:
                        return float('inf')
                    
                    # Simple distance calculation (not exact, but good for sorting)
                    lat_diff = abs(place_loc.get('lat', 0) - location['lat'])
                    lng_diff = abs(place_loc.get('lng', 0) - location['lng'])
                    return (lat_diff ** 2 + lng_diff ** 2) ** 0.5
                
                # Sort by distance
                all_places.sort(key=calculate_distance)
                
                # Filter out results that are too far (more aggressive for UAE)
                max_distance_km = 30 if self._is_in_uae_region(location) else 50
                filtered_places = []
                for place in all_places:
                    place_loc = place.get('geometry', {}).get('location', {})
                    if place_loc:
                        try:
                            from geopy.distance import geodesic
                            d = geodesic((location['lat'], location['lng']), (place_loc.get('lat'), place_loc.get('lng'))).kilometers
                            if d <= max_distance_km:
                                filtered_places.append(place)
                        except Exception:
                            # If distance calculation fails, include the place
                            filtered_places.append(place)
                all_places = filtered_places
            
            # Convert to our format
            out: List[Dict] = []
            for p in all_places[:10]:  # Limit to 10 results
                loc = p.get('geometry', {}).get('location', {})
                if not loc:
                    continue
                place = {
                    'name': p.get('name', 'Unknown place'),
                    'display_name': p.get('name', ''),
                    'address': p.get('formatted_address') or p.get('vicinity', ''),
                    'location': {'lat': loc.get('lat'), 'lng': loc.get('lng')},
                    'place_id': p.get('place_id'),
                    'types': p.get('types', []),
                    'rating': p.get('rating'),
                }
                # Calculate distance if we have a current location
                if location:
                    try:
                        from geopy.distance import geodesic
                        d = geodesic((location['lat'], location['lng']), (loc.get('lat'), loc.get('lng'))).meters
                        place['distance'] = round(d / 1000, 2)
                        place['distance_meters'] = int(d)
                    except Exception:
                        pass
                out.append(place)
            
            logger.info(f"Returning {len(out)} filtered results for '{query}'")
            return out
        except Exception as e:
            logger.error(f"Google Places search error: {e}")
            return []

    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """
        Get detailed information about a place
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Place details dictionary or None
        """
        try:
            if not place_id:
                return None
            resp = self.client.place(place_id=place_id)
            result = resp.get('result')
            if not result:
                return None
            loc = result.get('geometry', {}).get('location', {})
            return {
                'name': result.get('name', 'Destination'),
                'address': result.get('formatted_address', ''),
                'location': {'lat': loc.get('lat'), 'lng': loc.get('lng')},
                'place_id': result.get('place_id'),
                'phone': result.get('formatted_phone_number'),
                'website': result.get('website'),
                'rating': result.get('rating'),
                'reviews': result.get('reviews', [])
            }
        except Exception as e:
            logger.error(f"Google place details error: {e}")
            return None





