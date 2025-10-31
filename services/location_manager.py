"""
Location Manager Module
Handles favorite locations and location history management
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import Config

logger = logging.getLogger(__name__)

class LocationManager:
    """Manager for favorite locations and location history"""
    
    def __init__(self):
        """Initialize the location manager"""
        self.favorites_file = Config.FAVORITES_FILE
        self.history_file = 'data/location_history.json'
        self._ensure_data_directory()
        self._load_data()
    
    def _ensure_data_directory(self) -> None:
        """Ensure data directory exists"""
        try:
            os.makedirs('data', exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating data directory: {str(e)}")
    
    def _load_data(self) -> None:
        """Load favorites and history from files"""
        try:
            # Load favorites
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    self.favorites = json.load(f)
            else:
                self.favorites = []
            
            # Load history
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            else:
                self.history = []
            
            logger.info(f"Loaded {len(self.favorites)} favorites and {len(self.history)} history items")
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            self.favorites = []
            self.history = []
    
    def _save_favorites(self) -> bool:
        """Save favorites to file"""
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.favorites)} favorites")
            return True
            
        except Exception as e:
            logger.error(f"Error saving favorites: {str(e)}")
            return False
    
    def _save_history(self) -> bool:
        """Save history to file"""
        try:
            # Keep only last 100 items
            self.history = self.history[-100:]
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.history)} history items")
            return True
            
        except Exception as e:
            logger.error(f"Error saving history: {str(e)}")
            return False
    
    def add_favorite(self, location: Dict, custom_name: str = None) -> bool:
        """
        Add a location to favorites
        
        Args:
            location: Location dictionary with name, address, and coordinates
            custom_name: Custom name for the favorite location
            
        Returns:
            True if added successfully
        """
        try:
            # Check if location already exists in favorites
            existing = self.find_favorite_by_coordinates(
                location['location']['lat'], 
                location['location']['lng']
            )
            
            if existing:
                logger.warning(f"Location already in favorites: {existing['name']}")
                return False
            
            favorite = {
                'id': len(self.favorites) + 1,
                'name': custom_name or location['name'],
                'original_name': location['name'],
                'address': location.get('address', ''),
                'location': location['location'],
                'added_date': datetime.now().isoformat(),
                'usage_count': 0,
                'last_used': None,
                'place_id': location.get('place_id'),
                'rating': location.get('rating', 0),
                'types': location.get('types', [])
            }
            
            self.favorites.append(favorite)
            
            if self._save_favorites():
                logger.info(f"Added favorite: {favorite['name']}")
                return True
            else:
                # Remove from list if save failed
                self.favorites.pop()
                return False
                
        except Exception as e:
            logger.error(f"Error adding favorite: {str(e)}")
            return False
    
    def remove_favorite(self, favorite_id: int) -> bool:
        """
        Remove a favorite location
        
        Args:
            favorite_id: ID of the favorite to remove
            
        Returns:
            True if removed successfully
        """
        try:
            for i, favorite in enumerate(self.favorites):
                if favorite['id'] == favorite_id:
                    removed = self.favorites.pop(i)
                    logger.info(f"Removed favorite: {removed['name']}")
                    return self._save_favorites()
            
            logger.warning(f"Favorite with ID {favorite_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error removing favorite: {str(e)}")
            return False
    
    def get_favorites(self) -> List[Dict]:
        """
        Get all favorite locations
        
        Returns:
            List of favorite location dictionaries
        """
        return self.favorites.copy()
    
    def find_favorite_by_name(self, name: str) -> Optional[Dict]:
        """
        Find favorite location by name
        
        Args:
            name: Name to search for
            
        Returns:
            Favorite location dictionary or None
        """
        name_lower = name.lower()
        
        for favorite in self.favorites:
            if (name_lower in favorite['name'].lower() or 
                name_lower in favorite['original_name'].lower()):
                return favorite
        
        return None
    
    def find_favorite_by_coordinates(self, lat: float, lng: float, 
                                   tolerance: float = 0.001) -> Optional[Dict]:
        """
        Find favorite location by coordinates
        
        Args:
            lat: Latitude
            lng: Longitude
            tolerance: Coordinate tolerance for matching
            
        Returns:
            Favorite location dictionary or None
        """
        for favorite in self.favorites:
            fav_lat = favorite['location']['lat']
            fav_lng = favorite['location']['lng']
            
            if (abs(fav_lat - lat) < tolerance and 
                abs(fav_lng - lng) < tolerance):
                return favorite
        
        return None
    
    def update_favorite_usage(self, favorite_id: int) -> bool:
        """
        Update usage statistics for a favorite
        
        Args:
            favorite_id: ID of the favorite
            
        Returns:
            True if updated successfully
        """
        try:
            for favorite in self.favorites:
                if favorite['id'] == favorite_id:
                    favorite['usage_count'] += 1
                    favorite['last_used'] = datetime.now().isoformat()
                    return self._save_favorites()
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating favorite usage: {str(e)}")
            return False
    
    def get_most_used_favorites(self, limit: int = 5) -> List[Dict]:
        """
        Get most frequently used favorites
        
        Args:
            limit: Maximum number of favorites to return
            
        Returns:
            List of favorite dictionaries sorted by usage
        """
        try:
            sorted_favorites = sorted(
                self.favorites,
                key=lambda x: x['usage_count'],
                reverse=True
            )
            
            return sorted_favorites[:limit]
            
        except Exception as e:
            logger.error(f"Error getting most used favorites: {str(e)}")
            return []
    
    def add_to_history(self, location: Dict, action: str = 'visited') -> bool:
        """
        Add location to history
        
        Args:
            location: Location dictionary
            action: Action performed (visited, searched, navigated_to)
            
        Returns:
            True if added successfully
        """
        try:
            history_item = {
                'id': len(self.history) + 1,
                'name': location['name'],
                'address': location.get('address', ''),
                'location': location['location'],
                'action': action,
                'timestamp': datetime.now().isoformat(),
                'place_id': location.get('place_id'),
                'rating': location.get('rating', 0)
            }
            
            # Check if same location was recently added
            recent_duplicate = False
            if self.history:
                last_item = self.history[-1]
                if (last_item['name'] == history_item['name'] and
                    last_item['action'] == history_item['action']):
                    
                    # Check if added within last 5 minutes
                    last_time = datetime.fromisoformat(last_item['timestamp'])
                    current_time = datetime.now()
                    time_diff = (current_time - last_time).total_seconds()
                    
                    if time_diff < 300:  # 5 minutes
                        recent_duplicate = True
            
            if not recent_duplicate:
                self.history.append(history_item)
                return self._save_history()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding to history: {str(e)}")
            return False
    
    def get_recent_history(self, limit: int = 10, action: str = None) -> List[Dict]:
        """
        Get recent location history
        
        Args:
            limit: Maximum number of items to return
            action: Filter by action type (optional)
            
        Returns:
            List of recent history items
        """
        try:
            history = self.history.copy()
            
            if action:
                history = [item for item in history if item['action'] == action]
            
            # Sort by timestamp, most recent first
            history.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return history[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recent history: {str(e)}")
            return []
    
    def search_locations(self, query: str) -> Dict[str, List[Dict]]:
        """
        Search in favorites and history
        
        Args:
            query: Search query
            
        Returns:
            Dict with 'favorites' and 'history' lists
        """
        try:
            query_lower = query.lower()
            
            # Search favorites
            matching_favorites = []
            for favorite in self.favorites:
                if (query_lower in favorite['name'].lower() or
                    query_lower in favorite['original_name'].lower() or
                    query_lower in favorite.get('address', '').lower()):
                    matching_favorites.append(favorite)
            
            # Search history
            matching_history = []
            for item in self.history:
                if (query_lower in item['name'].lower() or
                    query_lower in item.get('address', '').lower()):
                    matching_history.append(item)
            
            # Remove duplicates from history and sort by timestamp
            unique_history = []
            seen_names = set()
            for item in reversed(matching_history):
                if item['name'] not in seen_names:
                    unique_history.append(item)
                    seen_names.add(item['name'])
            
            return {
                'favorites': matching_favorites,
                'history': unique_history[:5]  # Limit history results
            }
            
        except Exception as e:
            logger.error(f"Error searching locations: {str(e)}")
            return {'favorites': [], 'history': []}
    
    def export_data(self) -> Dict[str, Any]:
        """
        Export all location data
        
        Returns:
            Dict containing all favorites and history
        """
        return {
            'favorites': self.favorites,
            'history': self.history,
            'export_date': datetime.now().isoformat()
        }
    
    def import_data(self, data: Dict[str, Any]) -> bool:
        """
        Import location data
        
        Args:
            data: Data dictionary to import
            
        Returns:
            True if imported successfully
        """
        try:
            if 'favorites' in data:
                self.favorites = data['favorites']
            
            if 'history' in data:
                self.history = data['history']
            
            # Save both files
            favorites_saved = self._save_favorites()
            history_saved = self._save_history()
            
            logger.info("Location data imported successfully")
            return favorites_saved and history_saved
            
        except Exception as e:
            logger.error(f"Error importing data: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            total_favorites = len(self.favorites)
            total_history = len(self.history)
            
            most_used = self.get_most_used_favorites(1)
            most_used_name = most_used[0]['name'] if most_used else 'None'
            
            recent_activity = len(self.get_recent_history(limit=7))  # Last 7 items
            
            return {
                'total_favorites': total_favorites,
                'total_history_items': total_history,
                'most_used_favorite': most_used_name,
                'recent_activity_count': recent_activity,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {}