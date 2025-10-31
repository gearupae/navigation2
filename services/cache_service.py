"""
Cache Service Module
Implements caching mechanisms to reduce API calls and improve performance
"""
import json
import os
import time
import hashlib
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)

class CacheService:
    """Service for caching API responses and application data"""
    
    def __init__(self):
        """Initialize the cache service"""
        self.cache_dir = Config.CACHE_DIR
        self.cache_timeout = Config.CACHE_TIMEOUT
        self._ensure_cache_directory()
        
        # In-memory cache for frequently accessed data
        self.memory_cache = {}
        self.memory_cache_timestamps = {}
        
        logger.info("Cache service initialized")
    
    def _ensure_cache_directory(self) -> None:
        """Ensure cache directory exists"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating cache directory: {str(e)}")
    
    def _generate_cache_key(self, prefix: str, data: Dict) -> str:
        """
        Generate cache key from data
        
        Args:
            prefix: Cache key prefix
            data: Data to generate key from
            
        Returns:
            Cache key string
        """
        try:
            # Sort data for consistent key generation
            sorted_data = json.dumps(data, sort_keys=True)
            hash_object = hashlib.md5(sorted_data.encode())
            return f"{prefix}_{hash_object.hexdigest()}"
        except Exception as e:
            logger.error(f"Error generating cache key: {str(e)}")
            return f"{prefix}_{int(time.time())}"
    
    def _get_cache_file_path(self, cache_key: str) -> str:
        """Get full path to cache file"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _is_cache_valid(self, cache_data: Dict) -> bool:
        """
        Check if cache data is still valid
        
        Args:
            cache_data: Cached data dictionary
            
        Returns:
            True if cache is valid
        """
        try:
            if 'timestamp' not in cache_data or 'ttl' not in cache_data:
                return False
            
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            expiry_time = cache_time + timedelta(seconds=cache_data['ttl'])
            
            return datetime.now() < expiry_time
        except Exception as e:
            logger.error(f"Error checking cache validity: {str(e)}")
            return False
    
    def get(self, cache_key: str, use_memory: bool = True) -> Optional[Any]:
        """
        Get data from cache
        
        Args:
            cache_key: Cache key
            use_memory: Whether to check memory cache first
            
        Returns:
            Cached data or None if not found/expired
        """
        try:
            # Check memory cache first
            if use_memory and cache_key in self.memory_cache:
                if self._is_memory_cache_valid(cache_key):
                    logger.debug(f"Memory cache hit: {cache_key}")
                    return self.memory_cache[cache_key]
                else:
                    # Remove expired memory cache
                    self._remove_from_memory_cache(cache_key)
            
            # Check file cache
            cache_file = self._get_cache_file_path(cache_key)
            
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                if self._is_cache_valid(cache_data):
                    logger.debug(f"File cache hit: {cache_key}")
                    
                    # Store in memory cache for faster access
                    if use_memory:
                        self._store_in_memory_cache(cache_key, cache_data['data'])
                    
                    return cache_data['data']
                else:
                    # Remove expired cache file
                    os.remove(cache_file)
                    logger.debug(f"Removed expired cache: {cache_key}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache: {str(e)}")
            return None
    
    def set(self, cache_key: str, data: Any, ttl: int = None, use_memory: bool = True) -> bool:
        """
        Store data in cache
        
        Args:
            cache_key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (uses default if None)
            use_memory: Whether to also store in memory cache
            
        Returns:
            True if stored successfully
        """
        try:
            ttl = ttl or self.cache_timeout
            
            cache_data = {
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'ttl': ttl,
                'cache_key': cache_key
            }
            
            # Store in file cache
            cache_file = self._get_cache_file_path(cache_key)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            # Store in memory cache
            if use_memory:
                self._store_in_memory_cache(cache_key, data, ttl)
            
            logger.debug(f"Cached data: {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            return False
    
    def _store_in_memory_cache(self, cache_key: str, data: Any, ttl: int = None) -> None:
        """Store data in memory cache"""
        try:
            ttl = ttl or self.cache_timeout
            
            self.memory_cache[cache_key] = data
            self.memory_cache_timestamps[cache_key] = {
                'timestamp': datetime.now(),
                'ttl': ttl
            }
            
            # Clean up old memory cache entries
            self._cleanup_memory_cache()
            
        except Exception as e:
            logger.error(f"Error storing in memory cache: {str(e)}")
    
    def _is_memory_cache_valid(self, cache_key: str) -> bool:
        """Check if memory cache entry is valid"""
        try:
            if cache_key not in self.memory_cache_timestamps:
                return False
            
            cache_info = self.memory_cache_timestamps[cache_key]
            expiry_time = cache_info['timestamp'] + timedelta(seconds=cache_info['ttl'])
            
            return datetime.now() < expiry_time
        except Exception as e:
            logger.error(f"Error checking memory cache validity: {str(e)}")
            return False
    
    def _remove_from_memory_cache(self, cache_key: str) -> None:
        """Remove entry from memory cache"""
        try:
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
            if cache_key in self.memory_cache_timestamps:
                del self.memory_cache_timestamps[cache_key]
        except Exception as e:
            logger.error(f"Error removing from memory cache: {str(e)}")
    
    def _cleanup_memory_cache(self, max_entries: int = 100) -> None:
        """Clean up old memory cache entries"""
        try:
            if len(self.memory_cache) <= max_entries:
                return
            
            # Remove expired entries first
            expired_keys = []
            for key in list(self.memory_cache.keys()):
                if not self._is_memory_cache_valid(key):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_from_memory_cache(key)
            
            # If still too many entries, remove oldest ones
            if len(self.memory_cache) > max_entries:
                sorted_keys = sorted(
                    self.memory_cache_timestamps.keys(),
                    key=lambda k: self.memory_cache_timestamps[k]['timestamp']
                )
                
                remove_count = len(self.memory_cache) - max_entries
                for key in sorted_keys[:remove_count]:
                    self._remove_from_memory_cache(key)
            
        except Exception as e:
            logger.error(f"Error cleaning up memory cache: {str(e)}")
    
    def delete(self, cache_key: str) -> bool:
        """
        Delete cached data
        
        Args:
            cache_key: Cache key to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            deleted = False
            
            # Remove from memory cache
            if cache_key in self.memory_cache:
                self._remove_from_memory_cache(cache_key)
                deleted = True
            
            # Remove from file cache
            cache_file = self._get_cache_file_path(cache_key)
            if os.path.exists(cache_file):
                os.remove(cache_file)
                deleted = True
            
            if deleted:
                logger.debug(f"Deleted cache: {cache_key}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting cache: {str(e)}")
            return False
    
    def clear_all(self) -> bool:
        """
        Clear all cached data
        
        Returns:
            True if cleared successfully
        """
        try:
            # Clear memory cache
            self.memory_cache.clear()
            self.memory_cache_timestamps.clear()
            
            # Clear file cache
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, filename)
                    os.remove(file_path)
            
            logger.info("Cleared all cache data")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired cache files
        
        Returns:
            Number of files cleaned up
        """
        try:
            cleaned_count = 0
            
            # Clean up expired memory cache
            expired_keys = []
            for key in list(self.memory_cache.keys()):
                if not self._is_memory_cache_valid(key):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_from_memory_cache(key)
                cleaned_count += 1
            
            # Clean up expired file cache
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                        
                        if not self._is_cache_valid(cache_data):
                            os.remove(file_path)
                            cleaned_count += 1
                    except Exception as e:
                        # Remove corrupted cache files
                        os.remove(file_path)
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired cache entries")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {str(e)}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            memory_count = len(self.memory_cache)
            
            file_count = 0
            total_size = 0
            
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_count += 1
                    file_path = os.path.join(self.cache_dir, filename)
                    total_size += os.path.getsize(file_path)
            
            return {
                'memory_cache_entries': memory_count,
                'file_cache_entries': file_count,
                'total_cache_size_bytes': total_size,
                'total_cache_size_mb': round(total_size / (1024 * 1024), 2),
                'cache_directory': self.cache_dir,
                'default_ttl_seconds': self.cache_timeout
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {}
    
    # Specialized caching methods for different data types
    
    def cache_places_search(self, query: str, location: Dict, results: List[Dict]) -> bool:
        """Cache Google Places search results"""
        cache_key = self._generate_cache_key('places_search', {
            'query': query.lower(),
            'lat': round(location['lat'], 4),
            'lng': round(location['lng'], 4)
        })
        return self.set(cache_key, results, ttl=1800)  # 30 minutes
    
    def get_cached_places_search(self, query: str, location: Dict) -> Optional[List[Dict]]:
        """Get cached Google Places search results"""
        cache_key = self._generate_cache_key('places_search', {
            'query': query.lower(),
            'lat': round(location['lat'], 4),
            'lng': round(location['lng'], 4)
        })
        return self.get(cache_key)
    
    def cache_route(self, start: Dict, end: Dict, route_data: Dict) -> bool:
        """Cache navigation route"""
        cache_key = self._generate_cache_key('route', {
            'start_lat': round(start['lat'], 4),
            'start_lng': round(start['lng'], 4),
            'end_lat': round(end['lat'], 4),
            'end_lng': round(end['lng'], 4)
        })
        return self.set(cache_key, route_data, ttl=3600)  # 1 hour
    
    def get_cached_route(self, start: Dict, end: Dict) -> Optional[Dict]:
        """Get cached navigation route"""
        cache_key = self._generate_cache_key('route', {
            'start_lat': round(start['lat'], 4),
            'start_lng': round(start['lng'], 4),
            'end_lat': round(end['lat'], 4),
            'end_lng': round(end['lng'], 4)
        })
        return self.get(cache_key)
    
    def cache_geocoding(self, address: str, result: Dict) -> bool:
        """Cache geocoding results"""
        cache_key = self._generate_cache_key('geocoding', {'address': address.lower()})
        return self.set(cache_key, result, ttl=86400)  # 24 hours
    
    def get_cached_geocoding(self, address: str) -> Optional[Dict]:
        """Get cached geocoding results"""
        cache_key = self._generate_cache_key('geocoding', {'address': address.lower()})
        return self.get(cache_key)