# Navigation Assistant for Visually Impaired Users

A comprehensive voice-controlled navigation application designed specifically for visually impaired users. This application provides turn-by-turn navigation instructions using voice commands and text-to-speech feedback.

## Features

### Core Functionality
- **Voice Command Navigation**: Navigate to any location using simple voice commands
- **Google Places Integration**: Search for destinations using Google Maps API
- **OpenStreetMap Navigation**: Get turn-by-turn directions using OpenRouteService API
- **Real-time Speech Feedback**: Clear, natural voice instructions throughout navigation
- **Location Detection**: Automatic GPS location detection via web browser

### Advanced Features
- **Smart Caching**: Reduces API calls and improves performance
- **Favorites Management**: Save frequently visited locations
- **Location History**: Track previously searched and visited places
- **Nearby Search**: Find nearest restaurants, hospitals, banks, etc.
- **Multi-option Selection**: Choose from multiple search results when available

### Voice Commands

#### Navigation Commands
- `"Go to [destination]"` - Navigate to a specific place (e.g., "Go to Mzyad Mall")
- `"Navigate to [destination]"` - Alternative navigation command
- `"Take me to [destination]"` - Another navigation variant

#### Search Commands
- `"Find [place type]"` - Search for specific types of places
- `"Search for [query]"` - General search command
- `"Nearest [place type]"` - Find nearby places (e.g., "Nearest hospital")

#### Navigation Control
- `"Repeat"` - Repeat the current navigation instruction
- `"Next"` - Get the next navigation instruction
- `"Where am I?"` - Get current location information
- `"Stop navigation"` - Cancel the current route

#### Location Management
- `"Save location"` - Save current destination to favorites
- `"Save this place"` - Alternative save command

#### Help
- `"Help"` - Hear all available voice commands

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Google Maps API key
- OpenRouteService API key
- Microphone access
- Internet connection

### API Keys Required

#### Google Maps API
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Places API
4. Create credentials (API Key)
5. Restrict the key to Places API for security

#### OpenRouteService API
1. Visit [OpenRouteService](https://openrouteservice.org/)
2. Sign up for a free account
3. Generate an API key
4. Note the daily request limits

### Installation

1. **Clone/Download the project**
   ```bash
   cd /home/gearup/Work/navigation2
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit the `.env` file and add your API keys:
   ```
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
   OPENROUTESERVICE_API_KEY=your_openrouteservice_api_key_here
   ```

4. **Install system dependencies**
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install python3-pyaudio portaudio19-dev espeak espeak-data
   ```
   
   **macOS:**
   ```bash
   brew install portaudio
   ```
   
   **Windows:**
   - Install PyAudio from precompiled wheel
   - Text-to-speech should work out of the box

5. **Test microphone access**
   ```bash
   python -c "import speech_recognition as sr; print('Microphone test:', sr.Microphone.list_microphone_names())"
   ```

### Running the Application

1. **Start the Flask web server**
   ```bash
   python app.py
   ```

2. **Open your web browser**
   - Navigate to `http://localhost:5000`
   - Allow microphone access when prompted
   - Allow location access when prompted

3. **Start navigation**
   - Click "Start Navigation" button
   - Wait for microphone calibration
   - Begin speaking voice commands

## Usage Guide

### Initial Setup
1. Open the application in your web browser
2. Allow microphone and location access
3. Click "Start Navigation"
4. Wait for the system to calibrate your microphone
5. Listen for "Voice navigation ready" confirmation

### Basic Navigation
1. Say: `"Go to [destination name]"`
2. If multiple options are found, choose by saying the option number
3. Listen to the route summary
4. Follow the turn-by-turn voice instructions
5. Say `"Repeat"` if you need to hear an instruction again

### Example Voice Commands
- `"Go to Starbucks"` - Navigate to nearest Starbucks
- `"Nearest hospital"` - Find closest hospital options
- `"Where am I?"` - Get current location
- `"Save location"` - Save current destination to favorites

### Safety Tips
- Use headphones to hear instructions clearly
- Keep one ear free to hear surrounding sounds
- Stay aware of your environment while navigating
- Have a backup navigation method available

## Technical Architecture

### Components
- **Flask Web Application** (`app.py`): Web server and API endpoints
- **Navigation Controller** (`navigation_controller.py`): Main application logic
- **Location Service** (`services/location_service.py`): GPS and geocoding
- **Places Service** (`services/places_service.py`): Google Places API integration
- **Navigation Service** (`services/navigation_service.py`): OpenRouteService integration
- **Speech Service** (`services/speech_service.py`): Voice recognition and TTS
- **Location Manager** (`services/location_manager.py`): Favorites and history
- **Cache Service** (`services/cache_service.py`): Performance optimization

### APIs Used
- **Google Places API**: Location search and place details
- **OpenRouteService API**: Turn-by-turn navigation
- **Browser Geolocation API**: GPS location detection
- **Web Speech API**: Voice recognition (browser-based)

## Configuration

### Environment Variables
- `GOOGLE_MAPS_API_KEY`: Google Maps API key
- `OPENROUTESERVICE_API_KEY`: OpenRouteService API key
- `SPEECH_RATE`: Text-to-speech rate (default: 150)
- `SPEECH_VOLUME`: Text-to-speech volume (default: 0.9)
- `CACHE_TIMEOUT`: Cache expiration in seconds (default: 3600)

### Customization Options
- Modify voice recognition sensitivity in `speech_service.py`
- Adjust TTS settings in `config.py`
- Change cache timeouts for different data types
- Customize voice command patterns

## Troubleshooting

### Common Issues

#### Microphone Not Working
- Check browser permissions
- Ensure microphone is not muted
- Try refreshing the page
- Check system audio settings

#### Location Not Detected
- Allow location access in browser
- Check GPS/location services are enabled
- Try the "Get Location" button manually
- Ensure internet connection is stable

#### Voice Recognition Issues
- Speak clearly and at moderate pace
- Reduce background noise
- Ensure microphone is close enough
- Try calibrating microphone again

#### API Errors
- Verify API keys are correct
- Check API quotas and usage limits
- Ensure internet connection is stable
- Check API service status

### Error Codes
- `400`: Bad request (missing parameters)
- `401`: Unauthorized (invalid API key)
- `403`: Forbidden (quota exceeded)
- `500`: Internal server error

## Development

### Project Structure
```
navigation2/
├── app.py                      # Flask web application
├── config.py                   # Configuration settings
├── navigation_controller.py    # Main application controller
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── README.md                  # This file
├── services/                  # Core services
│   ├── location_service.py
│   ├── places_service.py
│   ├── navigation_service.py
│   ├── speech_service.py
│   ├── location_manager.py
│   └── cache_service.py
├── templates/                 # HTML templates
│   └── index.html
├── static/                    # Static files (CSS, JS)
├── data/                      # User data (favorites, history)
└── cache/                     # Cache files
```

### Adding New Features
1. Create new service in `services/` directory
2. Add to navigation controller
3. Create API endpoints in `app.py`
4. Update frontend interface
5. Add voice commands to speech service

## Privacy and Security

### Data Handling
- Location data is processed locally
- API calls are made server-side only
- User data is stored locally in JSON files
- No personal data is transmitted to third parties

### Security Features
- API keys are stored server-side
- CORS enabled for frontend access
- Input validation on all endpoints
- Rate limiting can be added if needed

## License and Credits

### APIs Used
- Google Maps Platform (Places API)
- OpenRouteService (routing and directions)
- Browser Geolocation API
- Web Speech API

### Python Libraries
- Flask: Web framework
- SpeechRecognition: Voice recognition
- pyttsx3: Text-to-speech
- googlemaps: Google Maps API client
- openrouteservice: OpenRouteService API client
- geopy: Geocoding and distance calculations

## Support

For issues, feature requests, or questions:

1. Check the troubleshooting section above
2. Verify API keys and permissions
3. Check browser console for errors
4. Test with different browsers
5. Ensure all dependencies are installed

## Future Enhancements

- Offline navigation support
- Multi-language support
- Mobile app version
- Integration with public transportation
- Accessibility improvements
- Voice profile customization