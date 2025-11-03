"""
Flask Web Application for Navigation System
Provides web interface for the blind navigation application
"""
import logging
import os
from flask import Flask, request, jsonify, render_template, make_response, send_file
from flask_cors import CORS
from navigation_controller import NavigationController
from config import Config
import requests
import threading
from uuid import uuid4
import io
import os
import json
import base64
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger = logging.getLogger(__name__)
    logger.info("✅ Environment variables loaded from .env file")
except ImportError:
    pass  # dotenv not installed, env vars must be set manually
try:
    from PIL import Image
except Exception:
    Image = None
try:
    from gtts import gTTS
except Exception:
    gTTS = None

# Optional Google Places
from services.google_places_service import GooglePlacesService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for frontend access
CORS(app)

# Per-session navigation controllers
controllers = {}
controllers_lock = threading.Lock()

# Request caching to reduce redundant processing
request_cache = {}
cache_lock = threading.Lock()
CACHE_DURATION = 2  # seconds

def _get_sid(create_if_missing: bool = False) -> str:
    sid = (
        request.cookies.get('sid')
        or request.headers.get('X-Client-ID')
        or request.args.get('sid')
    )
    if not sid and create_if_missing:
        sid = str(uuid4())
    return sid

def _get_controller(create: bool = False):
    sid = _get_sid(create_if_missing=create)
    logger.info(f"_get_controller called - create: {create}, sid: {sid}")
    if not sid:
        logger.warning("No session ID available")
        return None, None
    with controllers_lock:
        ctrl = controllers.get(sid)
        logger.info(f"Controller lookup - sid: {sid}, found: {ctrl is not None}")
        if not ctrl and create:
            logger.info(f"Creating new controller for session {sid}")
            ctrl = NavigationController(test_mode=False)
            controllers[sid] = ctrl
            logger.info(f"Controller created and stored for session {sid}")
    return sid, ctrl

def _get_cached_response(cache_key: str):
    """Get cached response if still valid"""
    with cache_lock:
        if cache_key in request_cache:
            entry = request_cache[cache_key]
            # Support both old (data, ts) and new (data, ts, ttl) formats
            if isinstance(entry, tuple) and len(entry) == 3:
                cached_data, timestamp, ttl = entry
                ttl = ttl or CACHE_DURATION
            else:
                cached_data, timestamp = entry
                ttl = CACHE_DURATION
            if (datetime.now() - timestamp).total_seconds() < ttl:
                return cached_data
            else:
                # Remove expired cache
                del request_cache[cache_key]
    return None

def _cache_response(cache_key: str, response_data, duration: int = None):
    """Cache response data"""
    with cache_lock:
        request_cache[cache_key] = (response_data, datetime.now(), duration or CACHE_DURATION)

def initialize_navigation():
    """Ensure a controller exists for this session"""
    try:
        _, ctrl = _get_controller(create=True)
        if ctrl:
            logger.info("Navigation controller initialized for session")
    except Exception as e:
        logger.error(f"Failed to initialize navigation controller: {str(e)}")

@app.route('/')
def index():
    """Serve the main application page and assign a fresh session id each load"""
    sid = str(uuid4())
    resp = make_response(render_template('index.html'))
    resp.set_cookie('sid', sid, samesite='Lax')
    return resp

@app.route('/google')
def google_page():
    """Standalone page for Google Places workflow - ENSURE unique session per user"""
    # CRITICAL: Check if user already has session, create new one if not
    existing_sid = (
        request.cookies.get('sid')
        or request.headers.get('X-Client-ID')
    )
    
    if existing_sid:
        # Reuse existing session
        sid = existing_sid
        logger.info(f"Google page: Reusing existing session {sid}")
    else:
        # Create NEW unique session for this user
        sid = str(uuid4())
        logger.info(f"Google page: Created NEW session {sid} for new user")
    
    resp = make_response(render_template('google.html'))
    # Set session cookie with long expiry and secure flags
    resp.set_cookie(
        'sid', 
        sid, 
        max_age=86400,  # 24 hours
        samesite='Lax',
        httponly=False  # Allow JavaScript to read it
    )
    return resp

@app.route('/outdoor')
def outdoor_navigation():
    """Complete outdoor navigation page with all functionalities"""
    # Don't create a new session ID here - let /api/start handle it
    resp = make_response(render_template('outdoor_navigation.html'))
    return resp

@app.route('/api/start', methods=['POST'])
def start_navigation():
    """Start the navigation system for this session"""
    try:
        sid, ctrl = _get_controller(create=True)
        if not ctrl:
            return jsonify({'success': False, 'message': 'Failed to initialize navigation controller'}), 500
        success = ctrl.start()
        response = jsonify({
            'success': success,
            'message': 'Navigation system started successfully' if success else 'Failed to start navigation system',
            'session_id': sid
        })
        # Set session cookie
        response.set_cookie('sid', sid, samesite='Lax')
        return response
    except Exception as e:
        logger.error(f"Error starting navigation: {str(e)}")
        return jsonify({'success': False, 'message': f'Error starting navigation: {str(e)}'}), 500

@app.route('/api/stop', methods=['POST'])
def stop_navigation():
    """Stop the navigation system for this session"""
    try:
        _, ctrl = _get_controller(create=False)
        if ctrl:
            ctrl.stop()
        return jsonify({'success': True, 'message': 'Navigation system stopped'})
    except Exception as e:
        logger.error(f"Error stopping navigation: {str(e)}")
        return jsonify({'success': False, 'message': f'Error stopping navigation: {str(e)}'}), 500

@app.route('/api/location', methods=['POST'])
def set_location():
    """Set current user location for this session"""
    try:
        _, ctrl = _get_controller(create=True)
        data = request.get_json(silent=True) or {}
        if 'latitude' not in data or 'longitude' not in data:
            return jsonify({'success': False, 'message': 'Latitude and longitude are required'}), 400
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
        success = ctrl.set_current_location(latitude, longitude)
        return jsonify({'success': success, 'message': 'Location updated successfully' if success else 'Failed to update location'})
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid latitude or longitude values'}), 400
    except Exception as e:
        logger.error(f"Error setting location: {str(e)}")
        return jsonify({'success': False, 'message': f'Error setting location: {str(e)}'}), 500

@app.route('/api/location/from-ip', methods=['POST'])
def set_location_from_ip():
    """Approximate location using client IP (fallback)."""
    try:
        _, ctrl = _get_controller(create=True)
        
        # Determine client IP (handles proxies if any)
        xff = request.headers.get('X-Forwarded-For', '')
        client_ip = (xff.split(',')[0].strip() if xff else request.remote_addr) or ''
        
        # Query IP geolocation service
        # Use ipapi.co which supports specifying the IP in the path
        # Try ipapi.co
        url = f'https://ipapi.co/{client_ip}/json/' if client_ip else 'https://ipapi.co/json/'
        lat = lng = None
        try:
            resp = requests.get(url, timeout=5)
            if resp.ok:
                data = resp.json()
                lat = data.get('latitude') or data.get('lat')
                lng = data.get('longitude') or data.get('lng')
        except Exception:
            pass
        
        # Fallback to ipwho.is (no key required)
        if lat is None or lng is None:
            try:
                url2 = f'https://ipwho.is/{client_ip}' if client_ip else 'https://ipwho.is/'
                resp2 = requests.get(url2, timeout=5)
                if resp2.ok:
                    d2 = resp2.json()
                    if d2.get('success', True):
                        lat = d2.get('latitude')
                        lng = d2.get('longitude')
            except Exception:
                pass
        
        # Fallback to ipinfo.io (parse loc field)
        if lat is None or lng is None:
            try:
                url3 = f'https://ipinfo.io/{client_ip}/json' if client_ip else 'https://ipinfo.io/json'
                resp3 = requests.get(url3, timeout=5)
                if resp3.ok:
                    d3 = resp3.json()
                    if 'loc' in d3:
                        loc = d3['loc']
                        lat_str, lng_str = loc.split(',')
                        lat = float(lat_str)
                        lng = float(lng_str)
            except Exception:
                pass
        
        if lat is None or lng is None:
            return jsonify({'success': False, 'message': 'Could not determine location from IP'}), 502
        
        success = ctrl.set_current_location(float(lat), float(lng))
        return jsonify({
            'success': success,
            'source': 'ip',
            'ip': client_ip,
            'latitude': float(lat),
            'longitude': float(lng)
        }), 200
    except Exception as e:
        logger.error(f"Error setting IP-based location: {str(e)}")
        return jsonify({'success': False, 'message': f'IP location error: {str(e)}'}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current application status for this session"""
    try:
        sid, ctrl = _get_controller(create=False)
        logger.info(f"Status request - Session ID: {sid}, Controller exists: {ctrl is not None}")
        
        if not ctrl:
            return jsonify({
                'initialized': False, 
                'session_id': sid,
                'message': 'Navigation system not initialized'
            })
        status = ctrl.get_status()
        status['initialized'] = True
        status['session_id'] = sid
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({'initialized': False, 'error': str(e)}), 500

@app.route('/api/favorites', methods=['GET'])
def get_favorites():
    """Get user's favorite locations (per session)"""
    try:
        _, ctrl = _get_controller(create=False)
        if not ctrl:
            return jsonify({'success': False, 'message': 'Navigation system not initialized'}), 400
        favorites = ctrl.location_manager.get_favorites()
        return jsonify({'success': True, 'favorites': favorites})
        
    except Exception as e:
        logger.error(f"Error getting favorites: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting favorites: {str(e)}'
        }), 500

@app.route('/api/favorites/<int:favorite_id>', methods=['DELETE'])
def delete_favorite(favorite_id):
    """Delete a favorite location (per session)"""
    try:
        _, ctrl = _get_controller(create=False)
        if not ctrl:
            return jsonify({'success': False, 'message': 'Navigation system not initialized'}), 400
        success = ctrl.location_manager.remove_favorite(favorite_id)
        return jsonify({'success': success, 'message': 'Favorite deleted successfully' if success else 'Failed to delete favorite'})
        
    except Exception as e:
        logger.error(f"Error deleting favorite: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error deleting favorite: {str(e)}'
        }), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get user's location history (per session)"""
    try:
        _, ctrl = _get_controller(create=False)
        if not ctrl:
            return jsonify({'success': False, 'message': 'Navigation system not initialized'}), 400
        limit = request.args.get('limit', 10, type=int)
        action = request.args.get('action', None)
        history = ctrl.location_manager.get_recent_history(limit=limit, action=action)
        return jsonify({'success': True, 'history': history})
        
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting history: {str(e)}'
        }), 500

@app.route('/api/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get cache statistics (per session)"""
    try:
        _, ctrl = _get_controller(create=False)
        if not ctrl:
            return jsonify({'success': False, 'message': 'Navigation system not initialized'}), 400
        stats = ctrl.cache_service.get_cache_stats()
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting cache stats: {str(e)}'
        }), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all cached data (per session)"""
    try:
        _, ctrl = _get_controller(create=False)
        if not ctrl:
            return jsonify({'success': False, 'message': 'Navigation system not initialized'}), 400
        success = ctrl.cache_service.clear_all()
        return jsonify({'success': success, 'message': 'Cache cleared successfully' if success else 'Failed to clear cache'})
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error clearing cache: {str(e)}'
        }), 500

@app.route('/api/cache/cleanup', methods=['POST'])
def cleanup_cache():
    """Clean up expired cache entries (per session)"""
    try:
        _, ctrl = _get_controller(create=False)
        if not ctrl:
            return jsonify({'success': False, 'message': 'Navigation system not initialized'}), 400
        cleaned_count = ctrl.cache_service.cleanup_expired()
        return jsonify({'success': True, 'cleaned_count': cleaned_count, 'message': f'Cleaned up {cleaned_count} expired cache entries'})
        
    except Exception as e:
        logger.error(f"Error cleaning up cache: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error cleaning up cache: {str(e)}'
        }), 500

@app.route('/api/text-command', methods=['POST'])
def process_text_command():
    """Process text command input (per session)"""
    try:
        _, ctrl = _get_controller(create=True)
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({'success': False, 'message': 'Command text is required'}), 400
        command_text = data['command'].strip()
        if not command_text:
            return jsonify({'success': False, 'message': 'Command cannot be empty'}), 400
        logger.info(f"Processing text command: {command_text}")
        is_navigation_command = any(phrase in command_text.lower() for phrase in ['go to', 'navigate to', 'take me to'])
        ctrl._handle_voice_command(command_text)
        status = ctrl.get_status()
        if is_navigation_command and status.get('waiting_for_selection') and status.get('search_results'):
            return jsonify({'success': True, 'message': f'Found {len(status["search_results"])} destinations', 'results': status['search_results']})
        else:
            return jsonify({'success': True, 'message': f'Command "{command_text}" processed successfully', 'command': command_text})
        
    except Exception as e:
        logger.error(f"Error processing text command: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing command: {str(e)}'
        }), 500

@app.route('/api/navigation/current-instruction', methods=['GET'])
def get_current_navigation_instruction():
    """Get current navigation instruction (per session)"""
    try:
        sid, ctrl = _get_controller(create=False)
        
        # Check cache first to reduce redundant processing
        cache_key = f"instruction_{sid}"
        cached_response = _get_cached_response(cache_key)
        if cached_response:
            logger.info(f"Returning cached instruction for session {sid}")
            return jsonify(cached_response)
        
        logger.info(f"Current instruction request - Session ID: {sid}, Controller exists: {ctrl is not None}")
        
        if not ctrl:
            # Try to recreate the controller if it's missing
            logger.warning(f"Controller missing for session {sid}, attempting to recreate...")
            _, ctrl = _get_controller(create=True)
            if not ctrl:
                response = {'success': False, 'message': 'Navigation system not initialized'}
                return jsonify(response), 400
        
        if not ctrl.is_navigating:
            logger.info(f"Navigation not active for session {sid}")
            response = {'success': False, 'message': 'No active navigation'}
            _cache_response(cache_key, response)
            return jsonify(response)
        
        instruction = ctrl.navigation_service.get_current_instruction()
        logger.info(f"Got instruction for session {sid}: {instruction is not None}")
        
        if instruction:
            # Apply narration improvement for blind users to all navigation instructions
            if isinstance(instruction, dict):
                original_speech = instruction.get('speech_instruction', '')
                original_instruction = instruction.get('instruction', '')
                
                # Improve both speech and text instructions
                if original_speech:
                    improved_speech = improve_narration_for_blind_users(original_speech)
                    improved_speech = add_intersection_guidance(improved_speech, instruction)
                    instruction['speech_instruction'] = improved_speech
                
                if original_instruction:
                    improved_instruction = improve_narration_for_blind_users(original_instruction)
                    improved_instruction = add_intersection_guidance(improved_instruction, instruction)
                    instruction['instruction'] = improved_instruction
            
            response = {
                'success': True,
                'instruction': instruction
            }
            _cache_response(cache_key, response)
            return jsonify(response)
        else:
            response = {
                'success': False,
                'message': 'No current instruction available'
            }
            _cache_response(cache_key, response)
            return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting navigation instruction: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting instruction: {str(e)}'
        }), 500

@app.route('/api/navigation/route', methods=['GET'])
def get_current_route():
    """Get current navigation route data for map display (per session)"""
    try:
        sid, ctrl = _get_controller(create=False)
        logger.info(f"[ROUTE] Request received - sid={sid}, controller_exists={ctrl is not None}")
        if not ctrl:
            logger.warning(f"[ROUTE] No controller for sid={sid}")
            return jsonify({'success': False, 'message': 'Navigation system not initialized'}), 400
        if not ctrl.is_navigating:
            logger.info(f"[ROUTE] No active navigation - sid={sid}")
            return jsonify({'success': False, 'message': 'No active navigation'})
        route_data = ctrl.navigation_service.current_route
        steps_count = (len(route_data.get('instructions', [])) if isinstance(route_data, dict) else 0) if route_data else 0
        logger.info(f"[ROUTE] Route present={route_data is not None}, steps={steps_count} - sid={sid}")
        
        if route_data:
            try:
                total_distance = route_data.get('total_distance') if isinstance(route_data, dict) else None
                total_duration = route_data.get('total_duration') if isinstance(route_data, dict) else None
                logger.info(f"[ROUTE] Returning route - distance={total_distance}, duration={total_duration}, steps={steps_count} - sid={sid}")
            except Exception:
                pass
            return jsonify({
                'success': True,
                'route': route_data
            })
        else:
            logger.info(f"[ROUTE] No current route available - sid={sid}")
            return jsonify({
                'success': False,
                'message': 'No current route available'
            })
        
    except Exception as e:
        logger.error(f"Error getting navigation route: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting route: {str(e)}'
        }), 500

@app.route('/api/navigation/advance', methods=['POST'])
def advance_instruction():
    """Manually advance to the next navigation instruction (per session testing)"""
    try:
        _, ctrl = _get_controller(create=False)
        if not ctrl:
            return jsonify({'success': False, 'message': 'Navigation system not initialized'}), 400
        if not ctrl.is_navigating:
            return jsonify({'success': False, 'message': 'No active navigation'})
        success = ctrl.manual_advance_instruction()
        return jsonify({'success': success, 'message': 'Advanced to next instruction' if success else 'Reached destination'})
        
    except Exception as e:
        logger.error(f"Error advancing instruction: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error advancing instruction: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        from datetime import datetime
        _, ctrl = _get_controller(create=False)
        health_status = {
            'status': 'healthy',
            'navigation_initialized': ctrl is not None,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/google/search', methods=['POST'])
def google_search():
    """Search places using Google Places API without affecting OSM workflow."""
    try:
        api_key = Config.GOOGLE_MAPS_API_KEY
        if not api_key:
            return jsonify({'success': False, 'message': 'GOOGLE_MAPS_API_KEY not configured'}), 400
        _, ctrl = _get_controller(create=True)
        current_location = None
        try:
            current_location = ctrl.location_service.get_current_location()
        except Exception:
            current_location = None
        data = request.get_json(silent=True) or {}
        query = (data.get('query') or '').strip()
        radius = int(data.get('radius', 5000))
        if not query:
            return jsonify({'success': False, 'message': 'query is required'}), 400
        gps = GooglePlacesService(api_key)
        results = gps.search_places(query=query, location=current_location, radius=radius)
        # Populate controller selection state so existing UI can select 1..n
        with controllers_lock:
            ctrl.search_results = results
            ctrl.waiting_for_selection = True
        return jsonify({'success': True, 'results': results, 'provider': 'google'})
    except Exception as e:
        logger.error(f"Google search error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/routing-mode', methods=['POST'])
def set_routing_mode():
    """Set routing mode (walking or driving)"""
    try:
        _, ctrl = _get_controller(create=True)
        if not ctrl:
            return jsonify({'success': False, 'message': 'Navigation system not initialized'}), 400
        
        data = request.get_json(silent=True) or {}
        mode = data.get('mode', 'foot').lower()
        
        # Validate mode
        valid_modes = {
            'foot': 'foot',
            'walk': 'foot',
            'walking': 'foot',
            'car': 'car',
            'drive': 'car',
            'driving': 'car',
            'vehicle': 'car'
        }
        
        if mode not in valid_modes:
            return jsonify({
                'success': False,
                'message': f'Invalid mode: {mode}. Use "walking" or "driving"'
            }), 400
        
        ctrl.routing_mode = valid_modes[mode]
        mode_name = 'Walking' if ctrl.routing_mode == 'foot' else 'Driving'
        
        logger.info(f"Routing mode changed to: {ctrl.routing_mode} ({mode_name})")
        
        return jsonify({
            'success': True,
            'mode': ctrl.routing_mode,
            'mode_name': mode_name,
            'message': f'Routing mode set to {mode_name}'
        })
    except Exception as e:
        logger.error(f"Error setting routing mode: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/routing-mode', methods=['GET'])
def get_routing_mode():
    """Get current routing mode"""
    try:
        _, ctrl = _get_controller(create=False)
        if not ctrl:
            return jsonify({'success': True, 'mode': 'foot', 'mode_name': 'Walking'})
        
        mode_name = 'Walking' if ctrl.routing_mode == 'foot' else 'Driving'
        return jsonify({
            'success': True,
            'mode': ctrl.routing_mode,
            'mode_name': mode_name
        })
    except Exception as e:
        logger.error(f"Error getting routing mode: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/google/navigate', methods=['POST'])
def google_navigate():
    """Start navigation to a Google place_id or lat/lng via OSRM."""
    try:
        api_key = Config.GOOGLE_MAPS_API_KEY
        if not api_key:
            return jsonify({'success': False, 'message': 'GOOGLE_MAPS_API_KEY not configured'}), 400
        _, ctrl = _get_controller(create=True)
        data = request.get_json(silent=True) or {}
        place_id = data.get('place_id')
        name = data.get('name')
        lat = data.get('lat')
        lng = data.get('lng')
        # Ensure current location is available
        cur = None
        try:
            cur = ctrl.location_service.get_current_location()
        except Exception:
            cur = None
        
        # If backend doesn't have location, try to get it from request body (frontend sends it)
        if not cur:
            # Frontend should send current location in the navigate request
            current_lat = data.get('current_lat')
            current_lng = data.get('current_lng')
            if current_lat and current_lng:
                logger.info(f"Using location from request: [{current_lat}, {current_lng}]")
                ctrl.location_service.set_current_location(current_lat, current_lng)
                cur = {'lat': current_lat, 'lng': current_lng}
            else:
                logger.warning(f"No location available for session - backend: {cur}, request: lat={current_lat}, lng={current_lng}")
                return jsonify({
                    'success': False, 
                    'message': 'Current location not available. Please allow location access and try again.'
                }), 400
        if place_id:
            gps = GooglePlacesService(api_key)
            det = gps.get_place_details(place_id)
            if not det:
                return jsonify({'success': False, 'message': 'place not found'}), 404
            name = det['name']
            lat = det['location']['lat']
            lng = det['location']['lng']
        if name and lat is not None and lng is not None:
            # Build place dict compatible with controller
            place = {
                'name': name,
                'location': {'lat': float(lat), 'lng': float(lng)}
            }
            ctrl._start_navigation_to_place(place)
            # Verify started
            if not ctrl.is_navigating:
                return jsonify({'success': False, 'message': 'Navigation could not start (no route).'}), 500
            return jsonify({'success': True, 'message': f'Started navigation to {name}'})
        return jsonify({'success': False, 'message': 'Provide place_id or name+lat+lng'}), 400
    except Exception as e:
        logger.error(f"Google navigate error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

VISION_STATE = {}

@app.route('/api/vision/toggle', methods=['POST'])
def vision_toggle():
    try:
        sid, _ = _get_controller(create=True)
        enabled = bool((request.get_json(silent=True) or {}).get('enabled'))
        VISION_STATE[sid] = {'enabled': enabled, 'last': None}
        return jsonify({'success': True, 'enabled': enabled})
    except Exception as e:
        logger.error(f"Vision toggle error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/vision/status', methods=['GET'])
def vision_status():
    sid, _ = _get_controller(create=False)
    st = VISION_STATE.get(sid) if sid else None
    return jsonify({'success': True, 'enabled': bool(st and st.get('enabled')), 'last': (st or {}).get('last')})

@app.route('/api/vision/frame', methods=['POST'])
def vision_frame():
    try:
        sid, ctrl = _get_controller(create=True)
        if not sid or not ctrl:
            return jsonify({'success': False, 'message': 'session not ready'}), 400
        st = VISION_STATE.get(sid)
        if not st or not st.get('enabled'):
            return jsonify({'success': False, 'message': 'vision disabled'}), 400
        file = request.files.get('image')
        ctx = request.form.get('context')
        if not file:
            return jsonify({'success': False, 'message': 'no image'}), 400
        if Image is None:
            return jsonify({'success': False, 'message': 'Pillow not installed'}), 500
        
        # Optimize image loading - resize large images IMMEDIATELY to prevent memory issues
        try:
            img = Image.open(file.stream).convert('RGB')
            # Aggressively resize for faster API calls (max 800x600 - enough for obstacle detection)
            max_size = (800, 600)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                logger.info(f"🖼️ Resized image from original to {img.size} for faster processing")
                logger.info(f"Resized image from {file.stream} to {img.size}")
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return jsonify({'success': False, 'message': f'Invalid image: {str(e)}'}), 400
        
        nav = ctrl.navigation_service.get_current_instruction()
        
        # Use timeout for vision processing to prevent worker hangs
        try:
            guidance = analyze_image_with_context(img, nav, ctx)
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            # Strict: do not fabricate guidance
            return jsonify({'success': False, 'message': 'vision unavailable'}), 503
        
        fused = fuse_nav_and_vision(nav, guidance)
        narration = (fused.get('narration') or '').strip()

        # Decide whether to speak (throttle and only on changes)
        hazards = fused.get('hazards') or []
        steer = fused.get('suggested_heading') or 'straight'
        step_key = ''
        try:
            if isinstance(nav, dict):
                step_key = str(nav.get('id') or nav.get('index') or nav.get('instruction') or nav.get('speech_instruction') or '')
        except Exception:
            step_key = ''
        hazard_key = '|'.join(sorted([str(h) for h in hazards])) + f':{steer}'
        generic = narration.lower() in ('proceed carefully.', 'proceed straight carefully.', 'proceed carefully')

        now = datetime.now()
        last_spoken = (st or {}).get('last_spoken') or {}
        last_ts = last_spoken.get('ts')
        try:
            elapsed = (now - datetime.fromisoformat(last_ts)).total_seconds() if last_ts else None
        except Exception:
            elapsed = None

        should_speak = False
        # Prioritize vision guidance - speak more frequently for obstacles
        if hazards and hazard_key != last_spoken.get('hazard_key'):
            should_speak = True
        elif steer and steer != 'straight' and steer != last_spoken.get('steer'):
            should_speak = True
        elif step_key and step_key != last_spoken.get('step_key'):
            should_speak = True
        # Skip generic filler guidance
        if generic and not should_speak:
            should_speak = False
        # Enforce minimum gap (shorter for obstacles, longer for route changes)
        min_gap = 1 if hazards else 3  # Reduced gaps for more responsive guidance
        if should_speak and (elapsed is None or elapsed >= min_gap) and narration:
            ctrl.speech_service.speak(narration, priority='high')
            st['last_spoken'] = {
                'narration': narration,
                'hazard_key': hazard_key,
                'step_key': step_key,
                'steer': steer,
                'ts': now.isoformat(),
            }

        st['last'] = {'narration': narration, 'hazards': fused.get('hazards'), 'ts': now.isoformat(), 'provider': guidance.get('provider')}
        return jsonify({'success': True, **fused, 'provider': guidance.get('provider'), 'spoken': bool(should_speak and (elapsed is None or elapsed >= min_gap) and narration)})
    except Exception as e:
        logger.error(f"Vision frame error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ================= Vision helpers (Grok + fusion) =================
from datetime import datetime

def analyze_image_with_context(img, nav, ctx_json):
    provider = os.getenv('VISION_PROVIDER', 'grok').lower()
    heuristic_enabled = (os.getenv('VISION_HEURISTIC_ENABLED', 'false').lower() == 'true')
    if provider in ('grok', 'xai', 'grok-2-vision'):
        try:
            res = grok_vision(img, nav, ctx_json)
            if isinstance(res, dict):
                res.setdefault('provider', 'grok')
            return res
        except Exception as e:
            logger.error(f"Grok vision failed: {e}")
            if not heuristic_enabled:
                # Strict: do not return heuristic/mocked guidance
                raise
    # Optional fallback: on-device heuristic (only if explicitly enabled)
    if heuristic_enabled:
        res = heuristic_vision(img, nav, ctx_json)
        res.setdefault('provider', 'heuristic')
        return res
    # Strict mode and no valid provider
    raise RuntimeError('Vision analysis unavailable')


def grok_vision(img, nav, ctx_json):
    api_key = os.getenv('GROK_API_KEY')
    if not api_key:
        raise RuntimeError('GROK_API_KEY not set')
    # Encode image with aggressive compression for faster upload
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=45, optimize=True)  # Aggressive compression for speed
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    logger.info(f"📸 Encoded image size: {len(img_b64)} chars (JPEG quality=50)")
    # Compose prompt
    nav_text = ''
    try:
        if isinstance(nav, dict):
            nav_text = nav.get('speech_instruction') or nav.get('instruction') or ''
    except Exception:
        pass
    #prompt = (
    #    "You are a navigation assistant for a BLIND pedestrian. Analyze the image and current navigation instruction. "
    #    "Return STRICT JSON with keys: hazards (list, short items like 'bin center'), "
    #    "suggested_heading (one of: 'left','slightly left','straight','slightly right','right'), "
    #    "narration (<=25 words, clear, actionable, and specific for blind users)."
    #    "\n\nCRITICAL RULES FOR BLIND USERS:"
    #    "\n1. NEVER say 'watch for' or 'look for' - they cannot see"
    #    "\n2. Instead of 'Turn right at intersection', say 'Walk straight until you feel the intersection, then turn right'"
    #    "\n3. Use tactile guidance: 'feel the intersection', 'listen for guidance', 'walk slowly'"
    #    "\n4. Give step-by-step actions: 'walk straight', 'then turn', 'continue for X steps'"
    #    "\n5. Use distance in steps or meters: 'walk 20 steps', 'walk 50 meters'"
    #    "\n6. For obstacles, say 'I will guide you around the obstacle' not 'watch for obstacles'"
    #    f"\nCurrent navigation instruction: {nav_text}\nContext: {ctx_json or ''}"
    #)
    prompt = (
        "You are a blind-pedestrian navigation assistant. "
        "Analyze the image and provide real-time obstacle detection and guidance. Return STRICT JSON:\n"
        '{"hazards":["..."],"suggested_heading":"left|slightly left|straight|slightly right|right","narration":"≤15 words"}\n'
        "CRITICAL RULES:\n"
        "- Detect obstacles: people, vehicles, poles, barriers, uneven surfaces, steps, curbs\n"
        "- ALWAYS provide steering direction when obstacles are detected\n"
        "- For obstacles: suggest 'left', 'right', 'slightly left', or 'slightly right' to avoid them\n"
        "- For clear paths: suggest 'straight' to continue route\n"
        "- Consider the current route direction when suggesting steering\n"
        "- Use simple, direct language\n"
        "- NO visual references: never say 'watch', 'look', 'see'\n"
        "- Keep instructions brief and actionable\n"
        "- Prioritize safety over route following\n"
        f"Current route instruction: {nav_text}\nContext: {ctx_json or ''}"
    )
    # xAI Grok API (OpenAI-compatible style)
    url = os.getenv('GROK_API_BASE', 'https://api.x.ai/v1/chat/completions')
    model = os.getenv('GROK_VISION_MODEL', 'grok-2-vision')
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    body = {
        'model': model,
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}
                ]
            }
        ],
        'temperature': 0.2
    }
    # Fast fail for real-time guidance; configurable via VISION_TIMEOUT_SECONDS
    try:
        vision_timeout = float(os.getenv('VISION_TIMEOUT_SECONDS', '5'))
    except Exception:
        vision_timeout = 5.0
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=vision_timeout)
    resp.raise_for_status()
    data = resp.json()
    # Extract assistant content
    try:
        content = data['choices'][0]['message']['content']
        # Some providers return text not structured; try to parse JSON from it
        jstart = content.find('{')
        jend = content.rfind('}')
        if jstart >= 0 and jend > jstart:
            parsed = json.loads(content[jstart:jend+1])
        else:
            parsed = {'narration': content.strip()[:120]}
        # Normalize
        parsed.setdefault('hazards', [])
        parsed.setdefault('suggested_heading', 'straight')
        parsed.setdefault('narration', 'Proceed carefully.')
        parsed.setdefault('provider', 'grok')
        return parsed
    except Exception as e:
        logger.error(f"Grok parse error: {e}; raw={data}")
        # Respect strict mode: do not fabricate narration
        if os.getenv('VISION_HEURISTIC_ENABLED', 'false').lower() == 'true':
            return {'hazards': [], 'suggested_heading': 'straight', 'narration': 'Proceed carefully.', 'provider': 'grok'}
        raise RuntimeError('Vision parse failed')


def heuristic_vision(img, nav, ctx_json):
    try:
        from PIL import ImageStat
        g = img.convert('L')  # grayscale
        w, h = g.size
        third = max(1, w // 3)
        boxes = [
            (0, 0, third, h),
            (third, 0, 2*third, h),
            (2*third, 0, w, h)
        ]
        means = [ImageStat.Stat(g.crop(b)).mean[0] for b in boxes]
        left, center, right = means
        hazards = []
        steer = 'straight'
        if center + 12 < max(left, right):
            hazards.append('dark obstacle ahead')
            steer = 'slightly left' if left > right else 'slightly right'
        else:
            if left + 15 < right:
                hazards.append('left side clutter')
                steer = 'slightly right'
            elif right + 15 < left:
                hazards.append('right side clutter')
                steer = 'slightly left'
        narration = None
        if hazards:
            narration = (steer.capitalize() + ' and continue.') if steer and steer != 'straight' else 'Proceed carefully.'
        return {
            'hazards': hazards,
            'suggested_heading': steer,
            'narration': narration or 'Proceed carefully.',
            'provider': 'heuristic'
        }
    except Exception as e:
        logger.error(f"Heuristic vision error: {e}")
        return {'hazards': [], 'suggested_heading': 'straight', 'narration': 'Proceed carefully.', 'provider': 'heuristic'}


def fuse_nav_and_vision(nav, vis):
    hazards = [str(h).strip() for h in (vis.get('hazards') or []) if str(h).strip()]
    steer = (vis.get('suggested_heading') or '').strip().lower() or 'straight'
    vn = (vis.get('narration') or '').strip()

    # Get current navigation instruction and distance
    nav_distance = 0
    nav_instruction = ''
    nav_direction = 'straight'
    
    try:
        if isinstance(nav, dict):
            nav_distance = nav.get('distance', 0)
            nav_instruction = nav.get('speech_instruction') or nav.get('instruction') or ''
            # Extract direction from instruction
            nav_direction = extract_direction_from_instruction(nav_instruction)
    except Exception:
        pass

    # Convert distance to steps (approximate: 1 step = 0.7 meters)
    steps_remaining = int(nav_distance / 0.7) if nav_distance > 0 else 0

    # Combine map instruction with vision analysis
    # Only prioritize vision if obstacles are actually detected
    if hazards and len(hazards) > 0:
        # Obstacles detected - include names and provide actionable avoidance guidance
        try:
            obstacle_names = ', '.join([humanize_hazard(h) for h in hazards])
            obstacle_prefix = f"Obstacles: {obstacle_names} ahead, " if len(hazards) > 1 else f"Obstacle: {obstacle_names} ahead, "
        except Exception:
            obstacle_prefix = "Obstacle ahead, "
        if steer != 'straight':
            # Give clear direction to avoid obstacle and continue route
            if steer == 'left':
                narration = f"{obstacle_prefix}move left, then continue {nav_direction}"
            elif steer == 'right':
                narration = f"{obstacle_prefix}move right, then continue {nav_direction}"
            elif steer == 'slightly left':
                narration = f"{obstacle_prefix}move slightly left, then continue {nav_direction}"
            elif steer == 'slightly right':
                narration = f"{obstacle_prefix}move slightly right, then continue {nav_direction}"
            else:
                narration = f"{obstacle_prefix}move {steer}, then continue {nav_direction}"
        else:
            # Obstacle detected but no clear steering - provide default avoidance guidance
            if nav_direction == 'left':
                narration = f"{obstacle_prefix}move right, then continue {nav_direction}"
            elif nav_direction == 'right':
                narration = f"{obstacle_prefix}move left, then continue {nav_direction}"
            else:
                # Default to slight left for straight routes
                narration = f"{obstacle_prefix}move slightly left, then continue {nav_direction}"
    else:
        # No obstacles - provide step-by-step guidance based on map instruction
        if steps_remaining > 0:
            if steps_remaining > 20:
                # Far from destination - give general direction
                narration = f"Walk {steps_remaining} steps {nav_direction}."
            elif steps_remaining > 10:
                # Getting closer - more specific
                narration = f"Walk {steps_remaining} steps {nav_direction}."
            elif steps_remaining > 5:
                # Very close - precise guidance
                narration = f"Walk {steps_remaining} steps {nav_direction}."
            else:
                # Almost there
                narration = f"Walk {steps_remaining} more steps {nav_direction}."
        else:
            # No distance info - use general instruction
            if nav_instruction:
                narration = make_route_instruction_brief(nav_instruction)
            else:
                narration = 'Continue straight ahead.'

    # Improve narration for blind users
    narration = improve_narration_for_blind_users(narration)
    
    # Add intersection guidance
    narration = add_intersection_guidance(narration, nav)

    return {
        'narration': narration, 
        'hazards': hazards, 
        'suggested_heading': steer,
        'steps_remaining': steps_remaining,
        'nav_direction': nav_direction
    }

def extract_direction_from_instruction(instruction):
    """Extract direction from navigation instruction"""
    if not instruction:
        return 'straight'
    
    instruction_lower = instruction.lower()
    if 'turn right' in instruction_lower or 'right' in instruction_lower:
        return 'right'
    elif 'turn left' in instruction_lower or 'left' in instruction_lower:
        return 'left'
    elif 'straight' in instruction_lower or 'continue' in instruction_lower:
        return 'straight'
    else:
        return 'straight'

def humanize_hazard(h: str) -> str:
    t = h.lower()
    if 'left side clutter' in t:
        return 'obstacles on your left'
    if 'right side clutter' in t:
        return 'obstacles on your right'
    if 'dark obstacle' in t or 'obstacle' in t:
        return 'an obstacle ahead'
    return h

def get_steering_guidance(steer: str) -> str:
    if steer == 'slightly left':
        return 'Move left'
    if steer == 'slightly right':
        return 'Move right'
    if steer == 'left':
        return 'Move left'
    if steer == 'right':
        return 'Move right'
    return 'Continue straight'

def make_route_instruction_brief(instruction: str) -> str:
    """Make route instructions more concise for real-time navigation"""
    # Remove distance details for smoother navigation
    import re
    
    # Remove "In X meters" patterns
    brief = re.sub(r'\bin\s+\d+\s*(meters?|m|feet?|ft)[,\s]*', '', instruction, flags=re.IGNORECASE)
    # Remove standalone distance mentions
    brief = re.sub(r'\d+\s*(meters?|m|feet?|ft)', '', brief, flags=re.IGNORECASE)
    
    # Remove leftover "In," or "in," at start
    brief = re.sub(r'^in[,\s]+', '', brief, flags=re.IGNORECASE)
    
    # Clean up multiple spaces and commas
    brief = re.sub(r'\s*,\s*', ', ', brief)  # Fix comma spacing
    brief = re.sub(r',\s*,', ',', brief)  # Remove double commas
    brief = re.sub(r'\s+', ' ', brief).strip()
    brief = brief.strip(',').strip()  # Remove leading/trailing commas
    
    # Make it more actionable
    if 'turn right' in brief.lower():
        return 'Turn right when you reach the intersection'
    elif 'turn left' in brief.lower():
        return 'Turn left when you reach the intersection'
    elif 'straight' in brief.lower():
        return 'Continue straight ahead'
    elif 'start' in brief.lower() and 'on' in brief.lower():
        # Keep start instructions simple
        return brief
    else:
        return brief

def improve_narration_for_blind_users(narration):
    """Improve navigation narration to be more clear and actionable for blind users."""
    if not narration:
        return narration
    
    # Common confusing phrases and their better alternatives for blind users
    improvements = {
        # Start/Depart instructions
        r'\bstart and go straight\b': 'begin walking straight ahead',
        r'\bstart\b': 'begin walking',
        r'\bdepart\b': 'begin walking',
        r'\bgo straight\b': 'walk straight ahead',
        r'\bcontinue straight\b': 'keep walking straight ahead',
        
        # Turn instructions - make them actionable with distance guidance
        r'\bturn right at the next intersection\b': 'walk straight until you feel the intersection, then turn right',
        r'\bturn left at the next intersection\b': 'walk straight until you feel the intersection, then turn left',
        r'\bturn slightly right at the next intersection\b': 'walk straight until you feel the intersection, then turn slightly right',
        r'\bturn slightly left at the next intersection\b': 'walk straight until you feel the intersection, then turn slightly left',
        r'\bturn right\b': 'turn right',
        r'\bturn left\b': 'turn left',
        r'\bturn slightly right\b': 'turn slightly right',
        r'\bturn slightly left\b': 'turn slightly left',
        
        # Distance and timing - make them more specific
        r'\bin (\d+) meters\b': r'walk approximately \1 meters',
        r'\bin about (\d+) meters\b': r'walk approximately \1 meters',
        r'\bin (\d+) min\b': r'walk for about \1 minutes',
        
        # Arrival instructions
        r'\byou have arrived at your destination\b': 'you have reached your destination',
        r'\byou have arrived\b': 'you have reached your destination',
        r'\barrive at your destination\b': 'you have reached your destination',
        
        # Road/Street names
        r'\bon the road\b': 'on the street',
        r'\bonto the road\b': 'onto the street',
        
        # Safety instructions - remove "watch for obstacles" since they can't see
        r'\bproceed carefully\b': 'walk slowly and listen for guidance',
        r'\bproceed straight carefully\b': 'walk straight ahead slowly and listen for guidance',
        r'\bwalk carefully and watch for obstacles\b': 'walk slowly and listen for guidance',
        r'\bwatch for obstacles\b': 'listen for guidance about obstacles',
        r'\bwatch for\b': 'listen for guidance about',
        
        # Remove contradictory instructions
        r'\bguide around.*?\.\s*keep walking straight ahead after avoiding\b': 'Move left to avoid obstacle',
        r'\bguide around.*?\.\s*continue straight after avoiding\b': 'Move left to avoid obstacle',
        r'\bguide around.*?\.\s*then continue straight\b': 'Move left to avoid obstacle',
    }
    
    import re
    improved = narration.lower()
    
    # Apply improvements
    for pattern, replacement in improvements.items():
        improved = re.sub(pattern, replacement, improved, flags=re.IGNORECASE)
    
    # Capitalize first letter
    if improved:
        improved = improved[0].upper() + improved[1:]
    
    # Ensure it ends with a period
    if improved and not improved.endswith('.'):
        improved += '.'
    
    return improved

def add_intersection_guidance(narration, nav_instruction=None):
    """Add specific guidance for intersections and turns."""
    if not narration:
        return narration
    
    # Check if this is a turn instruction
    turn_phrases = ['turn right', 'turn left', 'turn slightly right', 'turn slightly left']
    is_turn = any(phrase in narration.lower() for phrase in turn_phrases)
    
    if is_turn and 'intersection' in narration.lower():
        # Add step-by-step guidance for turns
        if 'turn right' in narration.lower():
            return narration.replace('turn right', 'turn right and walk 10 steps forward')
        elif 'turn left' in narration.lower():
            return narration.replace('turn left', 'turn left and walk 10 steps forward')
        elif 'turn slightly right' in narration.lower():
            return narration.replace('turn slightly right', 'turn slightly right and walk 10 steps forward')
        elif 'turn slightly left' in narration.lower():
            return narration.replace('turn slightly left', 'turn slightly left and walk 10 steps forward')
    
    return narration

# ================= Narration improvement endpoint =================
@app.route('/api/improve-narration', methods=['POST'])
def improve_narration():
    """Test endpoint to improve navigation narration for blind users."""
    try:
        data = request.get_json(silent=True) or {}
        original_narration = data.get('narration', '').strip()
        
        if not original_narration:
            return jsonify({'error': 'narration is required'}), 400
        
        improved_narration = improve_narration_for_blind_users(original_narration)
        improved_narration = add_intersection_guidance(improved_narration)
        
        return jsonify({
            'success': True,
            'original': original_narration,
            'improved': improved_narration,
            'changes_made': original_narration.lower() != improved_narration.lower()
        })
    except Exception as e:
        logger.error(f"Narration improvement error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-narration', methods=['GET'])
def test_narration():
    """Test endpoint with the specific problematic instruction."""
    try:
        test_instruction = "In 250 meters, Start and go straight"
        improved = improve_narration_for_blind_users(test_instruction)
        improved = add_intersection_guidance(improved)
        
        return jsonify({
            'success': True,
            'original': test_instruction,
            'improved': improved,
            'changes_made': test_instruction.lower() != improved.lower()
        })
    except Exception as e:
        logger.error(f"Test narration error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/navigation/unified-instruction', methods=['GET'])
def get_unified_instruction():
    """Get unified smart instruction combining map navigation and vision analysis."""
    try:
        sid, ctrl = _get_controller(create=False)
        
        # CRITICAL DEBUG: Log which session is being used
        logger.info(f"🔍 UNIFIED INSTRUCTION REQUEST - Session ID: {sid}, Controller exists: {ctrl is not None}")
        
        if not ctrl:
            logger.warning(f"❌ No controller found for session {sid}")
            return jsonify({'success': False, 'message': 'Navigation system not initialized'}), 400
        
        if not ctrl.is_navigating:
            # If vision is enabled and we have recent guidance, return that instead of failing
            vision_state = VISION_STATE.get(sid, {})
            last = (vision_state or {}).get('last')
            if vision_state.get('enabled') and last:
                logger.info(f"ℹ️ Session {sid} not navigating, but returning latest VISION guidance")
                return jsonify({
                    'success': True,
                    'instruction': last.get('narration') or 'Proceed carefully.',
                    'context': last.get('provider', 'vision'),
                    'priority': 'vision',
                    'vision_enabled': True
                })
            logger.info(f"ℹ️ Session {sid} is not navigating")
            return jsonify({'success': False, 'message': 'No active navigation'})
        
        # Get current navigation instruction
        nav_instruction = ctrl.navigation_service.get_current_instruction()
        
        # Get vision state to include in cache key (so instruction updates when obstacles change)
        vision_state = VISION_STATE.get(sid, {})
        vision_enabled = vision_state.get('enabled', False)
        last_vision = vision_state.get('last', {})
        obstacle_state = 'none'
        if vision_enabled and last_vision:
            hazards = last_vision.get('hazards', [])
            if hazards and len(hazards) > 0:
                # Include actual obstacle names in cache key so it updates when obstacles change
                obstacle_state = f"obs_{'_'.join(sorted(hazards[:3]))}"  # Use actual obstacle names
                logger.info(f"🚧 Obstacles detected: {hazards} → cache_state: {obstacle_state}")
        
        # Check if step index OR obstacle state changed - regenerate if either changed
        current_step_index = ctrl.navigation_service.current_step_index
        cache_key = f"instruction_{sid}_{current_step_index}_{obstacle_state}"
        
        # CRITICAL DEBUG: Log distance to waypoint and step index
        try:
            current_location = ctrl.location_service.get_current_location()
            if current_location and nav_instruction:
                waypoint_coords = nav_instruction.get('maneuver', {}).get('location') if isinstance(nav_instruction, dict) else None
                if waypoint_coords:
                    from math import radians, sin, cos, sqrt, atan2
                    lat1, lon1 = radians(current_location['lat']), radians(current_location['lng'])
                    lat2, lon2 = radians(waypoint_coords[1]), radians(waypoint_coords[0])
                    dlat, dlon = lat2 - lat1, lon2 - lon1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    distance_to_waypoint = 6371000 * 2 * atan2(sqrt(a), sqrt(1-a))
                    logger.info(f"🎯 [NAVIGATION] Step {current_step_index}: Distance to waypoint: {distance_to_waypoint:.1f}m, Obstacle state: {obstacle_state}")
        except Exception as e:
            logger.warning(f"Could not calculate waypoint distance: {e}")
        
        # Return cached instruction if step AND obstacle state haven't changed
        cached = _get_cached_response(cache_key)
        if cached:
            logger.info(f"✅ [CACHE HIT] Returning cached instruction for session {sid}, step {current_step_index}, obstacles: {obstacle_state}")
            return jsonify(cached)
        
        logger.info(f"📝 [CACHE MISS] Generating NEW instruction for session {sid}, step {current_step_index}")
        
        # Get vision state
        vision_state = VISION_STATE.get(sid, {})
        vision_enabled = vision_state.get('enabled', False)
        
        # Determine context and priority
        context = "Route following"
        priority = "map"
        
        # Get distance and time info FIRST
        distance = nav_instruction.get('distance', 0) if nav_instruction else 0
        duration = nav_instruction.get('duration', 0) if nav_instruction else 0

        # ---- Helpers for merging/translation ---------------------------------
        def contains_arabic(s: str) -> bool:
            return any('\u0600' <= ch <= '\u06FF' for ch in s or '')

        def translate_arabic_names(text: str) -> str:
            """Provide an English-friendly fallback when Arabic street names appear.
            This avoids TTS skipping unreadable names; no external API used.
            """
            if not text:
                return text
            if not contains_arabic(text):
                return text
            
            import re
            # Replace only Arabic characters (preserve spaces and other text)
            # Match sequences of Arabic characters (without spaces)
            result = re.sub(r'[\u0600-\u06FF]+', '[ARABIC]', text)
            
            # Remove duplicate placeholders that might be adjacent with only spaces between
            result = re.sub(r'\[ARABIC\](\s+\[ARABIC\])+', '[ARABIC]', result)
            
            # Replace placeholder with readable text
            result = result.replace('[ARABIC]', 'a local street')
            
            # Clean up extra spaces
            result = re.sub(r'\s+', ' ', result).strip()
            
            # Simplify common patterns
            result = result.replace('on a local street', 'on the local street')
            result = result.replace('onto a local street', 'onto the local street')
            
            # Add translation note if not already present
            if 'local street' in result and 'translated' not in result.lower():
                result = f"{result} (street name translated from Arabic)"
            
            return result
        
        # ONLY create fallback instruction if vision is OFF or LLM will fail
        # When vision is ON, LLM will handle EVERYTHING
        if not vision_enabled:
            # No vision - create simple route instruction as fallback
            context = "Route following (no vision)"
            priority = "map"
            if nav_instruction:
                nav_text = nav_instruction.get('speech_instruction') or nav_instruction.get('instruction') or ''
                instruction = translate_arabic_names(make_route_instruction_brief(nav_text))
            else:
                instruction = "Continue following your route."
        else:
            # Vision is ON - LLM will create the instruction, just set context
            last_vision = vision_state.get('last', {})
            hazards = last_vision.get('hazards', [])
            
            if hazards and len(hazards) > 0:
                context = "Live Vision: Obstacle detected"
                priority = "vision"
            else:
                context = "Live Vision: Path clear"
                priority = "map"
            
            # Placeholder - LLM will replace this
            instruction = "Processing live vision..."

        # --- Refine with Grok LLM for mode-appropriate instructions (HIGHLY RECOMMENDED) ---------------------
        grok_key = os.getenv('GROK_API_KEY') or os.getenv('XAI_API_KEY')
        
        # When vision is enabled, ALWAYS use LLM to combine everything into one instruction
        # When vision is disabled, LLM is optional (can use fallback)
        use_llm = grok_key and (vision_enabled or True)  # Always try LLM if key exists
        
        if not use_llm:
            logger.warning("⚠️ GROK_API_KEY not configured! Using fallback instructions (not optimal for users)")
            context = context + ' (NO LLM - fallback only)'
        else:
            # Process instruction through LLM for optimal output
            try:
                # Get routing mode from controller
                routing_mode = ctrl.routing_mode if hasattr(ctrl, 'routing_mode') else 'foot'
                is_walking = routing_mode == 'foot'
                
                compact_map = translate_arabic_names(
                    make_route_instruction_brief(
                        (nav_instruction.get('speech_instruction') if nav_instruction else '')
                        or (nav_instruction.get('instruction') if nav_instruction else '')
                        or instruction
                    )
                )
                last_vision = VISION_STATE.get(sid, {}).get('last', {})
                hazards = last_vision.get('hazards') or []
                steer = (last_vision.get('suggested_heading') or 'straight')
                sign_text = (last_vision.get('sign_text') or last_vision.get('narration') or '').strip()
                meters = int((nav_instruction or {}).get('distance') or distance or 0)
                
                # Calculate steps ONLY for walking mode
                steps_remaining = int(meters / 0.7) if (meters > 0 and is_walking) else 0

                # Build prompt with vision/image analysis if available
                vision_line = f"Vision analysis: "
                if hazards and len(hazards) > 0:
                    vision_line += f"OBSTACLES DETECTED: {', '.join(hazards)}; "
                else:
                    vision_line += f"path clear; "
                
                vision_line += f"suggested direction: {steer}"
                
                if sign_text:
                    vision_line += f"; sign detected: '{sign_text}'"

                # Build mode-appropriate prompt
                if is_walking:
                    # Walking mode - include steps, focus on pedestrian guidance
                    user_type = "BLIND pedestrian WALKING"
                    distance_info = f"Distance: {meters}m, {steps_remaining} steps"
                    distance_rule = "- Start with distance: 'In X meters' or 'Walk X steps'"
                    good_example = "'Walk 120 steps straight ahead for 84 meters.'"
                    avoid_rules = "- Avoid visual verbs (see, look, watch)\n- Use pedestrian terms (walk, turn, cross)"
                else:
                    # Driving mode - NO steps, focus on driving guidance
                    user_type = "driver in a VEHICLE"
                    distance_info = f"Distance: {meters}m ({meters/1000:.1f} km)"
                    distance_rule = "- Start with distance: 'In X meters' or 'Drive X kilometers'"
                    good_example = "'Drive 500 meters ahead, then turn right.'"
                    avoid_rules = "- Use driving terms (drive, turn, merge, exit)\n- NO walking/stepping references"

                # Build mode-appropriate examples
                if is_walking:
                    obstacle_example = "Obstacles: chair desk ahead, move slightly left, then walk 120 steps straight."
                    no_obstacle_example = "Walk 120 steps straight ahead for 84 meters."
                    action_verb = "Walk"
                else:
                    obstacle_example = "Obstacles detected ahead, move left, then continue driving."
                    no_obstacle_example = "Drive 48 meters straight ahead."
                    action_verb = "Drive"
                
                prompt = (
                    f"You are a navigation assistant for a {user_type}. "
                    "Create ONE natural, conversational sentence for audio guidance. "
                    f"Mode: {routing_mode.upper()}\n"
                    f"Route: {compact_map}\n"
                    f"Vision: {vision_line}\n"
                    f"{distance_info}\n\n"
                    "CRITICAL RULES:\n"
                    "IF OBSTACLES DETECTED:\n"
                    "  1. START: 'Obstacle detected on your [left/right/ahead]'\n"
                    "  2. THEN: 'move [left/right]'\n"
                    f"  3. THEN: 'then {action_verb.lower()} ahead'\n"
                    "IF NO OBSTACLES:\n"
                    f"  1. START with distance: '{action_verb} [distance] [direction]'\n\n"
                    "FORMATTING:\n"
                    "- Simple, natural English\n"
                    "- NEVER use: watch, see, look\n"
                    "- Maximum 15 words\n"
                    f"{avoid_rules}\n\n"
                    f"CORRECT with obstacle: '{obstacle_example}'\n"
                    f"CORRECT without obstacle: '{no_obstacle_example}'\n\n"
                    "Your sentence:"
                )
                url = os.getenv('GROK_API_BASE', 'https://api.x.ai/v1/chat/completions')
                model = os.getenv('GROK_TEXT_MODEL', 'grok-2-latest')
                headers = {'Authorization': f'Bearer {grok_key}', 'Content-Type': 'application/json'}
                body = {
                    'model': model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.1,  # Lower for more consistent, faster responses
                    'max_tokens': 50  # Reduced for faster response (20 words max)
                }
                
                # Call Grok LLM for blind-friendly output (with strict 5-second timeout)
                import time
                start_time = time.time()
                logger.info(f"🤖 [LLM] Calling Grok...")
                resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=5)  # STRICT 5-second timeout
                resp.raise_for_status()
                elapsed = time.time() - start_time
                logger.info(f"⏱️  [LLM] Response received in {elapsed:.2f}s")
                
                data_llm = resp.json()
                llm_text = (data_llm.get('choices') or [{}])[0].get('message', {}).get('content', '')
                llm_text = (llm_text or '').strip()
                
                if not llm_text:
                    logger.error("❌ [LLM] Grok returned empty response!")
                    raise Exception("LLM returned empty response")
                
                logger.info(f"✅ [LLM] Grok response: {llm_text}")
                
                # Ensure numeric distance appears; if missing, prepend a distance lead-in
                import re
                has_number = re.search(r"\b(\d+)\s*(meters?|m|steps?)\b", llm_text, re.IGNORECASE) is not None
                if not has_number and meters > 0:
                    lead = f"Proceed {meters} meters. "
                    if steps_remaining > 0:
                        lead = f"Proceed {meters} meters (about {steps_remaining} steps). "
                    llm_text = lead + llm_text
                    logger.info(f"📏 [LLM] Added distance prefix: {lead}")
                
                instruction = llm_text
                context = context + ' (LLM)' if '(LLM)' not in context else context
                
            except requests.exceptions.Timeout:
                logger.warning("⏱️  [LLM] Timeout after 5s - using fast fallback")
                # Create instant fallback instruction (mode-aware)
                if vision_enabled and hazards and len(hazards) > 0:
                    action = "drive" if not is_walking else "walk"
                    instruction = f"STOP! Obstacle detected. Move {steer}, then {action} ahead."
                else:
                    if is_walking and steps_remaining > 0:
                        # Walking mode: combine steps + direction smoothly
                        action = compact_map.lower() if compact_map else "continue"
                        instruction = f"Walk {steps_remaining} steps, then {action}."
                    else:
                        # Driving mode: include distance in instruction
                        if meters > 0:
                            action = compact_map.lower() if compact_map else "continue straight"
                            if meters >= 1000:
                                instruction = f"Drive {meters/1000:.1f} kilometers, then {action}."
                            else:
                                instruction = f"Drive {meters} meters, then {action}."
                        else:
                            instruction = compact_map if compact_map else "Continue straight ahead."
                context = context + ' (fast fallback)'
            except requests.exceptions.HTTPError as e:
                logger.error(f"❌ [LLM] API error: {e.response.status_code}")
                # Create instant fallback instruction (mode-aware)
                if vision_enabled and hazards and len(hazards) > 0:
                    action = "drive" if not is_walking else "walk"
                    instruction = f"STOP! Obstacle detected. Move {steer}, then {action} ahead."
                else:
                    if is_walking and steps_remaining > 0:
                        # Walking mode: combine steps + direction smoothly
                        action = compact_map.lower() if compact_map else "continue"
                        instruction = f"Walk {steps_remaining} steps, then {action}."
                    else:
                        # Driving mode: include distance in instruction
                        if meters > 0:
                            action = compact_map.lower() if compact_map else "continue straight"
                            if meters >= 1000:
                                instruction = f"Drive {meters/1000:.1f} kilometers, then {action}."
                            else:
                                instruction = f"Drive {meters} meters, then {action}."
                        else:
                            instruction = compact_map if compact_map else "Continue straight ahead."
                context = context + ' (error fallback)'
            except Exception as e:
                logger.error(f"❌ [LLM] Failed: {str(e)}")
                # Create instant fallback instruction (mode-aware)
                if vision_enabled and hazards and len(hazards) > 0:
                    action = "drive" if not is_walking else "walk"
                    instruction = f"STOP! Obstacle detected. Move {steer}, then {action} ahead."
                else:
                    if is_walking and steps_remaining > 0:
                        # Walking mode: combine steps + direction smoothly
                        action = compact_map.lower() if compact_map else "continue"
                        instruction = f"Walk {steps_remaining} steps, then {action}."
                    else:
                        # Driving mode: include distance in instruction
                        if meters > 0:
                            action = compact_map.lower() if compact_map else "continue straight"
                            if meters >= 1000:
                                instruction = f"Drive {meters/1000:.1f} kilometers, then {action}."
                            else:
                                instruction = f"Drive {meters} meters, then {action}."
                        else:
                            instruction = compact_map if compact_map else "Continue straight ahead."
                context = context + ' (fallback)'

        # Prepare response
        response_data = {
            'success': True,
            'instruction': instruction,
            'distance': distance,
            'duration': duration,
            'context': context,
            'priority': priority,
            'vision_enabled': vision_enabled
        }
        
        # Cache this instruction briefly - VERY short cache for immediate obstacle updates
        cache_duration = 1 if vision_enabled else 10  # 1 second with vision (almost no latency), 10 without
        _cache_response(cache_key, response_data, duration=cache_duration)
        logger.info(f"📦 Cached instruction for {cache_duration}s - Vision: {vision_enabled}, Obstacles: {obstacle_state}")
        
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"❌ CRITICAL ERROR in unified instruction:")
        logger.error(f"Session: {sid if 'sid' in locals() else 'unknown'}")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Traceback:\n{error_trace}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Internal error processing navigation instruction'
        }), 500

# ================= Existing TTS endpoint =================
@app.route('/api/tts', methods=['POST'])
def tts_api():
    """Server-side TTS: returns an MP3 for clients that cannot use Web Speech."""
    try:
        # Prefer fast offline engines for low latency
        data = request.get_json(silent=True) or {}
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({'error': 'text is required'}), 400
        # Choose engine: ESPEAK (fast, offline) → fallback to gTTS
        prefer = (os.getenv('TTS_ENGINE') or '').lower()
        use_espeak = prefer in ('espeak', 'fast', 'offline')
        # Quick language detect for espeak voice
        is_ar = any('\u0600' <= ch <= '\u06FF' for ch in text)
        voice = 'ar' if is_ar else 'en+f3'
        if use_espeak:
            try:
                import subprocess, tempfile
                wav_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                wav_tmp.close()
                cmd = ['espeak', '-s', '160', '-a', '180', '-v', voice, '-w', wav_tmp.name, text[:500]]
                subprocess.run(cmd, capture_output=True, timeout=5, check=True)
                with open(wav_tmp.name, 'rb') as f:
                    wav_bytes = f.read()
                try:
                    os.unlink(wav_tmp.name)
                except Exception:
                    pass
                return send_file(io.BytesIO(wav_bytes), mimetype='audio/wav', download_name='tts.wav')
            except Exception as e:
                logger.warning(f"Fast TTS (espeak) failed, falling back to gTTS: {e}")
        if gTTS is None:
            return jsonify({'error': 'No TTS engine available'}), 503
        # gTTS fallback (may be slower)
        lang = 'ar' if is_ar else 'en'
        fp = io.BytesIO()
        gTTS(text=text[:500], lang=lang, slow=False).write_to_fp(fp)
        fp.seek(0)
        return send_file(fp, mimetype='audio/mpeg', download_name='tts.mp3')
    except Exception as e:
        logger.error(f"TTS API error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'message': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'success': False,
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    try:
        # Ensure required directories exist
        os.makedirs('data', exist_ok=True)
        os.makedirs('cache', exist_ok=True)
        os.makedirs('templates', exist_ok=True)
        os.makedirs('static', exist_ok=True)
        
        # Initialize navigation controller before starting
        # Set test_mode=False to use real API services
        with app.app_context():
            pass  # Per-session initialization happens on demand
        
        # Start the Flask application
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=Config.DEBUG,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start Flask application: {str(e)}")
        raise
