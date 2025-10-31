#!/usr/bin/env python3
"""
Navigation Assistant Launcher
Comprehensive voice-controlled navigation application for visually impaired users
"""
import sys
import os
import logging
import argparse
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from app import app

def setup_logging(log_level=logging.INFO):
    """Setup application logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Setup file and console logging
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(f'logs/navigation_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from some libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized")
    return logger

def check_dependencies():
    """Check if all required dependencies are available"""
    required_modules = [
        'flask',
        'speech_recognition',
        'pyttsx3',
        'googlemaps',
        'openrouteservice',
        'geopy',
        'PIL'  # Pillow (for vision assist)
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ Missing required modules: {', '.join(missing_modules)}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    print("✅ All required dependencies are installed")
    return True

def validate_config():
    """Validate application configuration"""
    try:
        Config.validate_config()
        print("✅ Configuration validated successfully")
        return True
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please check your .env file and ensure all required API keys are set")
        return False

def print_welcome_message():
    """Print welcome message and instructions"""
    print("\n" + "="*60)
    print("🎯 NAVIGATION ASSISTANT FOR VISUALLY IMPAIRED USERS")
    print("="*60)
    print("\n📋 QUICK START GUIDE:")
    print("1. Open your web browser")
    print("2. Navigate to: http://localhost:5000")
    print("3. Allow microphone and location access")
    print("4. Click 'Start Navigation'")
    print("5. Begin using voice commands")
    
    print("\n🎤 EXAMPLE VOICE COMMANDS:")
    print('• "Go to Mzyad Mall"')
    print('• "Nearest hospital"')
    print('• "Where am I?"')
    print('• "Save location"')
    print('• "Help" (for full command list)')
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("• Keep your browser tab active for best performance")
    print("• Ensure stable internet connection")
    print("• Speak clearly and wait for responses")
    print("• Use headphones for better audio quality")
    
    print("\n" + "="*60)
    print("🚀 Starting Navigation Assistant...")
    print("="*60 + "\n")

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description="Navigation Assistant for Visually Impaired Users",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host address to bind to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to listen on (default: 5000)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--no-validation',
        action='store_true',
        help='Skip dependency and configuration validation'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = getattr(logging, args.log_level.upper())
    logger = setup_logging(log_level)
    
    logger.info("Starting Navigation Assistant application")
    
    # Print welcome message
    print_welcome_message()
    
    # Validate dependencies and configuration
    if not args.no_validation:
        if not check_dependencies():
            sys.exit(1)
        
        if not validate_config():
            sys.exit(1)
    
    try:
        # Ensure required directories exist
        directories = ['data', 'cache', 'logs', 'templates', 'static']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
        
        # Start the Flask application
        logger.info(f"Starting Flask server on {args.host}:{args.port}")
        
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True,
            use_reloader=False  # Disable reloader to avoid issues with voice recognition
        )
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        print("\n👋 Navigation Assistant stopped. Goodbye!")
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        print(f"\n❌ Error starting application: {e}")
        print("Please check the logs for more details.")
        sys.exit(1)

if __name__ == '__main__':
    main()