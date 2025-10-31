"""
Configuration settings for the Navigation App for Blind Users
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # API Keys
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
    OPENROUTESERVICE_API_KEY = os.getenv('OPENROUTESERVICE_API_KEY')
    
    # Cache Configuration
    CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', 3600))
    
    # Voice Configuration
    SPEECH_RATE = int(os.getenv('SPEECH_RATE', 150))
    SPEECH_VOLUME = float(os.getenv('SPEECH_VOLUME', 0.9))
    
    # Application Settings
    MAX_SEARCH_RESULTS = 5
    DEFAULT_SEARCH_RADIUS = 5000  # meters
    NAVIGATION_UPDATE_INTERVAL = 5  # seconds
    
    # File Paths
    FAVORITES_FILE = 'data/favorites.json'
    CACHE_DIR = 'cache/'
    
    @staticmethod
    def validate_config():
        """Validate required configuration"""
        # Only require Google Maps API key for Google Places functionality
        # OpenRouteService is not needed since we use free OSM services
        required_keys = ['GOOGLE_MAPS_API_KEY']
        missing_keys = []
        
        for key in required_keys:
            value = getattr(Config, key)
            if not value or value.startswith('test_'):
                missing_keys.append(key)
        
        if missing_keys:
            raise ValueError(f"Missing or invalid configuration: {', '.join(missing_keys)}")
        
        return True
