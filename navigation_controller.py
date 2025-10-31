"""
Navigation Controller
Main application logic that coordinates all components and handles user interactions
"""
import logging
import threading
import time
import math
from typing import Dict, List, Optional, Any
from datetime import datetime

from services.location_service import LocationService
from services.places_service import PlacesService
from services.osm_places_service import OSMPlacesService
from services.navigation_service import NavigationService
from services.osm_navigation_service import OSMNavigationService
from services.speech_service import SpeechService
from services.location_manager import LocationManager
from services.cache_service import CacheService
from services.mock_services import MockPlacesService, MockNavigationService
from config import Config

logger = logging.getLogger(__name__)

class NavigationController:
    """Main controller for the navigation application"""
    
    def __init__(self, test_mode=False):
        """Initialize the navigation controller"""
        try:
            self.test_mode = test_mode
            
            # Initialize all services
            self.location_service = LocationService()
            if not test_mode:
                # Use FREE OpenStreetMap services (no API keys needed!)
                self.places_service = OSMPlacesService()  # FREE Nominatim for place search
                self.navigation_service = OSMNavigationService()  # FREE OSRM for navigation
            else:
                # Use mock services in test mode
                self.places_service = MockPlacesService()
                self.navigation_service = MockNavigationService()
            self.speech_service = SpeechService()
            self.location_manager = LocationManager()
            self.cache_service = CacheService()
            
            # Application state
            self.current_destination = None
            self.is_navigating = False
            self.last_instruction_time = None
            self.last_announced_instruction = None  # Track last announced instruction
            self.navigation_thread = None
            
            # Interaction mode
            self.text_only_mode = True
            
            # User interaction state
            self.waiting_for_selection = False
            self.search_results = []
            self.pending_save_location = None
            
            # Location simulation for testing
            self.simulation_mode = False
            self.simulation_speed = 5.0  # meters per second (walking speed)
            self.last_simulation_update = None
            
            # Instruction throttling
            self.min_instruction_interval = 8.0  # seconds between spoken instructions
            
            # Track location changes for better waypoint detection
            self.last_known_location = None
            self.location_change_threshold = 8.0  # minimum meters moved to consider real movement (increased from 4.0)
            
            # Waypoint arrival detection - INCREASED to prevent GPS drift false positives
            self.arrival_distance_threshold = 25.0  # meters to consider waypoint reached (was 15.0)
            self.arrival_hysteresis = 15.0  # must have been > threshold + hysteresis before arriving (was 10.0)
            self._last_distance_to_waypoint = None
            self._last_arrival_check_time = None
            self.last_movement_time = None  # timestamp of last significant movement
            self.arrival_confirmations = 0  # require multiple confirmations before advancing
            self.required_arrival_confirmations = 2  # need 2 consecutive checks within threshold
            
            # Routing mode: 'foot' for walking, 'car' for driving
            self.routing_mode = 'foot'  # Default to walking (safest for blind users)
            
            logger.info("Navigation controller initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing navigation controller: {str(e)}")
            raise
    
    def start(self) -> bool:
        """
        Start the navigation application
        
        Returns:
            True if started successfully
        """
        try:
            logger.info(f"Starting navigation application (test_mode={self.test_mode})...")
            
            # No API key validation needed - using free OSM services!
            
            # Text-only command mode: no microphone/voice recognition
            logger.info("Text-only mode: Skipping voice recognition; keeping TTS for guidance")
            
            # Test TTS with a simple message
            logger.info("Testing TTS engine...")
            self.speech_service.speak(
                "Navigation system is ready.",
                priority="high"
            )
            
            logger.info("TTS announcement sent")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting application: {str(e)}")
            if not self.test_mode:
                self.speech_service.speak("Error starting navigation system.")
            return False
    
    def stop(self) -> None:
        """Stop the navigation application"""
        try:
            logger.info("Stopping navigation application...")
            
            # Stop navigation if active
            if self.is_navigating:
                self._stop_navigation()
            
            # Stop voice recognition
            self.speech_service.stop_continuous_listening()
            
            self.speech_service.speak("Navigation system stopped. Goodbye!")
            
        except Exception as e:
            logger.error(f"Error stopping application: {str(e)}")
    
    def set_current_location(self, latitude: float, longitude: float) -> bool:
        """
        Set the current user location
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            True if location was set successfully
        """
        try:
            success = self.location_service.set_current_location(latitude, longitude)
            
            if success:
                # Don't announce location updates during normal operation - too noisy!
                # Only log them silently
                logger.debug(f"Current location updated: {latitude}, {longitude}")
            else:
                logger.error(f"Failed to set current location: {latitude}, {longitude}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting current location: {str(e)}")
            return False
    
    def _handle_voice_command(self, command_text: str) -> None:
        """
        Handle voice or text command
        
        Args:
            command_text: Recognized or typed command text
        """
        try:
            logger.info(f"Processing voice command: {command_text}")
            
            # FIRST: Handle selection if waiting for user choice (highest priority)
            if self.waiting_for_selection:
                self._handle_selection_command(command_text)
                return
            
            # SECOND: Process standard commands
            command = self.speech_service.process_voice_command(command_text)
            
            if command['type'] == 'navigate':
                self._handle_navigate_command(command)
            elif command['type'] == 'search':
                self._handle_search_command(command)
            elif command['type'] == 'search_nearby':
                self._handle_nearby_search_command(command)
            elif command['type'] == 'repeat_instruction':
                self._handle_repeat_instruction()
            elif command['type'] == 'next_instruction':
                self._handle_next_instruction()
            elif command['type'] == 'current_location':
                self._handle_current_location_request()
            elif command['type'] == 'save_location':
                self._handle_save_location_request()
            elif command['type'] == 'stop_navigation':
                self._handle_stop_navigation()
            elif command['type'] == 'clear' or 'clear' in command.get('raw_command', '').lower():
                self._handle_clear_navigation()
            elif command['type'] == 'help':
                self._handle_help_request()
            elif command['type'] == 'simulate':
                self._handle_simulation_command(command)
            elif command['type'] == 'manual_advance':
                self._handle_manual_advance_command(command)
            elif command['type'] == 'reroute':
                self._handle_reroute_command(command)
            elif command['type'] == 'unknown':
                # THIRD: Text-only fallback for navigation (lowest priority)
                if self.text_only_mode:
                    destination = command.get('raw_command', '').strip()
                    if destination:
                        logger.info(f"Text-only fallback: navigating to '{destination}'")
                        return self._handle_navigate_command({'destination': destination})
                self._handle_unknown_command(command)
            elif command['type'] == 'error':
                self._handle_command_error(command)
            
        except Exception as e:
            logger.error(f"Error handling voice command: {str(e)}")
            self.speech_service.speak("I didn't understand that command. Please try again.")
    
    def _handle_navigate_command(self, command: Dict) -> None:
        """Handle navigation command"""
        try:
            destination_raw = command['destination']
            # Normalize destination (fix common typos, spacing, etc.)
            destination = self._normalize_destination_input(destination_raw)
            logger.info(f"Navigate request: raw='{destination_raw}' normalized='{destination}'")
            
            if not self.location_service.get_current_location():
                self.speech_service.speak("Please allow location access to use navigation.")
                return
            
            # Speak using a friendly case
            self.speech_service.speak(f"Searching for {destination.title()}...")
            
            # Search for the destination
            current_location = self.location_service.get_current_location()
            
            # Check cache first
            cached_results = self.cache_service.get_cached_places_search(destination, current_location)
            
            if cached_results:
                places = cached_results
                logger.info("Using cached search results")
            else:
                places = self.places_service.search_places(destination, current_location)
                if places:
                    self.cache_service.cache_places_search(destination, current_location, places)
            
            if not places:
                self.speech_service.speak(f"Sorry, I couldn't find {destination}. Please try a different search term.")
                return
            
            if len(places) == 1:
                # Single result, navigate directly
                self._start_navigation_to_place(places[0])
            else:
                # Multiple results, let user choose
                self._present_search_options(places)
            
        except Exception as e:
            logger.error(f"Error handling navigate command: {str(e)}")
            self.speech_service.speak("Error searching for destination.")
    
    def _handle_search_command(self, command: Dict) -> None:
        """Handle search command"""
        try:
            query = command['query']
            
            if not self.location_service.get_current_location():
                self.speech_service.speak("Please allow location access to search for places.")
                return
            
            self.speech_service.speak(f"Searching for {query}...")
            
            current_location = self.location_service.get_current_location()
            
            # Check cache first
            cached_results = self.cache_service.get_cached_places_search(query, current_location)
            
            if cached_results:
                places = cached_results
            else:
                places = self.places_service.search_places(query, current_location)
                if places:
                    self.cache_service.cache_places_search(query, current_location, places)
            
            if not places:
                self.speech_service.speak(f"Sorry, I couldn't find any {query} nearby.")
                return
            
            self._present_search_options(places, for_navigation=False)
            
        except Exception as e:
            logger.error(f"Error handling search command: {str(e)}")
            self.speech_service.speak("Error searching for places.")
    
    def _handle_nearby_search_command(self, command: Dict) -> None:
        """Handle nearby search command"""
        try:
            raw_query = command['query']
            # Normalize phrases like "nearest hospital", "closest restaurant near me"
            q = raw_query.lower()
            for token in ['nearest', 'closest', 'near me', 'nearby', 'around me', 'to me']:
                q = q.replace(token, '')
            query = q.strip() or raw_query
            
            if not self.location_service.get_current_location():
                self.speech_service.speak("Please allow location access to search for nearby places.")
                return
            
            self.speech_service.speak(f"Searching for {query}...")
            
            current_location = self.location_service.get_current_location()
            
            # Check cache first
            cached_results = self.cache_service.get_cached_places_search(query, current_location)
            
            if cached_results:
                places = cached_results
            else:
                places = self.places_service.search_places(query, current_location, radius=2000)
                if places:
                    self.cache_service.cache_places_search(query, current_location, places)
            
            if not places:
                self.speech_service.speak(f"Sorry, I couldn't find any {query} nearby.")
                return
            
            self._present_search_options(places)
            
        except Exception as e:
            logger.error(f"Error handling nearby search command: {str(e)}")
            self.speech_service.speak("Error searching for nearby places.")
    
    def _present_search_options(self, places: List[Dict], for_navigation: bool = True) -> None:
        """Present search options to user"""
        try:
            self.search_results = places
            self.waiting_for_selection = True
            
            current_location = self.location_service.get_current_location()
            
            # Only provide essential voice feedback since options are shown on screen
            if for_navigation:
                self.speech_service.speak(f"Found {len(places)} options. Please select a number.", priority="high")
            else:
                self.speech_service.speak(f"Found {len(places)} results. Please select a number.", priority="high")
            
            # Don't announce individual options since they're displayed on screen
            # This prevents voice overlapping and annoying repetition
            logger.info(f"Presenting {len(places)} search options on screen (silent mode)")
            
            # Log the options for debugging but don't speak them
            for i, place in enumerate(places[:5], 1):  # Limit to 5 options
                place_info = self.places_service.format_place_for_speech(
                    place, 
                    include_distance=True, 
                    current_location=current_location
                )
                logger.info(f"Option {i}: {place_info}")
            
            # In text-only mode, auto-select ONLY if there's exactly one result
            # If multiple results, always let user choose
            if self.text_only_mode and for_navigation and len(places) == 1:
                self.waiting_for_selection = False
                self.search_results = []
                self.speech_service.speak("Starting navigation to the only result found.")
                self._start_navigation_to_place(places[0])
                return
            
        except Exception as e:
            logger.error(f"Error presenting search options: {str(e)}")
            self.speech_service.speak("Error presenting options.")
    
    def _handle_selection_command(self, command_text: str) -> None:
        """Handle user selection from search results"""
        try:
            command_text = command_text.lower().strip()
            
            if 'cancel' in command_text:
                self.waiting_for_selection = False
                self.search_results = []
                self.speech_service.speak("Search cancelled.")
                return
            
            # Try to extract number
            for i in range(1, 6):
                if str(i) in command_text or self._number_to_word(i) in command_text:
                    if i <= len(self.search_results):
                        selected_place = self.search_results[i-1]
                        self.waiting_for_selection = False
                        self.search_results = []
                        
                        # Simple confirmation without details (details already on screen)
                        logger.info(f"User selected option {i}: {selected_place['name']}")
                        self._start_navigation_to_place(selected_place)
                        return
            
            # Brief error message without repeating instructions
            self.speech_service.speak("Please select a valid number or type cancel.", priority="high")
            
        except Exception as e:
            logger.error(f"Error handling selection: {str(e)}")
            self.speech_service.speak("Error processing selection.")
    
    def _number_to_word(self, num: int) -> str:
        """Convert number to word"""
        words = {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five'}
        return words.get(num, str(num))
    
    def _normalize_destination_input(self, text: str) -> str:
        """Normalize destination text (typo fixes, spacing)"""
        try:
            t = text.strip().lower()
            
            # Common command phrase fixes
            navigation_fixes = {
                'got o': 'go to',
                'goto': 'go to',
                'goto': 'go to',
                'gio to': 'go to',
                'gi to': 'go to',
                'take me to': '',
                'navigate to': '',
                'go to': '',  # Remove navigation phrases
                'find': '',
                'search for': ''
            }
            
            for wrong, right in navigation_fixes.items():
                t = t.replace(wrong, right)
            
            # Common location fixes
            location_corrections = {
                'mzyad': 'mazyad',
                'mzyad mall': 'mazyad mall',
                'mizyad': 'mazyad',
                'mazyed': 'mazyad',
                'mazayed': 'mazyad',
                'capitol': 'capital',
                'capitol mall': 'capital mall',
                'capitl': 'capital',
                'capatial': 'capital'
            }
            
            for wrong, right in location_corrections.items():
                t = t.replace(wrong, right)
            
            # Remove stray punctuation
            for ch in [',', ';', '|', '.']:
                t = t.replace(ch, ' ')
            
            # Collapse whitespace
            t = ' '.join(t.split())
            return t
        except Exception:
            return text
    
    def _start_navigation_to_place(self, place: Dict) -> None:
        """Start navigation to selected place"""
        try:
            current_location = self.location_service.get_current_location()
            
            if not current_location:
                self.speech_service.speak("Current location not available for navigation.")
                return
            
            self.speech_service.speak(f"Starting navigation to {place['name']}...")
            
            # Check for cached route
            cached_route = self.cache_service.get_cached_route(current_location, place['location'])
            
            # Only reuse cache if it matches current navigation engine (OSRM)
            if cached_route and isinstance(cached_route, dict) and cached_route.get('engine') == 'osrm':
                route = cached_route
                logger.info("Using cached route")
                # Important: Store the cached route in the navigation service
                self.navigation_service.current_route = cached_route
                self.navigation_service.current_step_index = 0
            else:
                if cached_route:
                    logger.info("Ignoring incompatible cached route; recalculating with OSRM")
                # Get directions using current routing mode (foot/car)
                logger.info(f"🚶/🚗 [NAVIGATION] Calculating route with mode: {self.routing_mode.upper()}")
                route = self.navigation_service.get_directions(current_location, place['location'], profile=self.routing_mode)
                if route:
                    logger.info(f"✅ [NAVIGATION] Route received: {route.get('distance', 0)}m, {route.get('duration', 0)}s")
                    self.cache_service.cache_route(current_location, place['location'], route)
            
            if not route:
                self.speech_service.speak("Unable to calculate route. Please try again.")
                return
            
            # Set destination and start navigation
            self.current_destination = place
            self.is_navigating = True
            self.last_announced_instruction = None  # Clear any previous instruction
            self.last_known_location = None  # Reset location tracking
            
            # Add to history
            self.location_manager.add_to_history(place, 'navigated_to')
            
            # Announce route summary
            summary = self.navigation_service.get_route_summary(route)
            if summary:
                self.speech_service.speak(summary)
            
            # Start navigation monitoring (only if we have instructions)
            logger.info(f"Route data: {route}")
            if route and route.get('instructions'):
                logger.info(f"Starting navigation with {len(route['instructions'])} instructions")
                # The navigation service already has the route from get_directions()
                logger.info(f"Navigation service current_route: {self.navigation_service.current_route is not None}")
                
                # Start navigation monitoring (which will announce the first instruction)
                self._start_navigation_monitoring()
            else:
                logger.warning("No navigation instructions available, stopping navigation")
                self.is_navigating = False
            
        except Exception as e:
            logger.error(f"Error starting navigation: {str(e)}")
            self.speech_service.speak("Error starting navigation.")
    
    def _announce_current_instruction(self) -> None:
        """Announce current navigation instruction"""
        try:
            # Get current location for navigation context
            current_location = self.location_service.get_current_location()
            
            # Get current route data from navigation service
            route_data = self.navigation_service.current_route
            
            logger.info(f"Announcing instruction - route_data: {route_data is not None}, current_location: {current_location is not None}")
            
            instruction = self.navigation_service.get_current_instruction(route_data, current_location)
            
            logger.info(f"Got instruction: {instruction is not None}")
            
            if instruction:
                # Handle both string (old format) and dict (new format) responses
                if isinstance(instruction, dict):
                    instruction_text = instruction.get('speech_instruction', str(instruction))
                else:
                    instruction_text = str(instruction)
                
                # Prevent announcing the same instruction multiple times
                if instruction_text == self.last_announced_instruction:
                    logger.debug(f"Skipping duplicate instruction: {instruction_text}")
                    return
                
                # Use high priority for navigation instructions to ensure they're heard
                self.speech_service.speak(instruction_text, priority="high")
                self.last_instruction_time = datetime.now()
                self.last_announced_instruction = instruction_text
                logger.info(f"Announced navigation instruction: {instruction_text}")
            elif self.is_navigating:
                # Check if we actually reached destination or if there's an error
                logger.warning("No instruction available but navigation is active - checking route status")
                if route_data and route_data.get('instructions'):
                    logger.error("Route has instructions but get_current_instruction returned None - this shouldn't happen")
                else:
                    logger.info("No route data available - stopping navigation")
                    self._handle_destination_reached()
            
        except Exception as e:
            logger.error(f"Error announcing instruction: {str(e)}")
    
    def _start_navigation_monitoring(self) -> None:
        """Start background thread to monitor navigation progress"""
        try:
            if self.navigation_thread and self.navigation_thread.is_alive():
                return
            
            self.navigation_thread = threading.Thread(target=self._navigation_monitor_loop)
            self.navigation_thread.daemon = True
            self.navigation_thread.start()
            
        except Exception as e:
            logger.error(f"Error starting navigation monitoring: {str(e)}")
    
    def _navigation_monitor_loop(self) -> None:
        """Background loop to monitor navigation progress"""
        logger.info("Navigation monitoring started")
        
        # Set baseline location to avoid immediate auto-advance without movement
        try:
            baseline_loc = self.location_service.get_current_location()
            if baseline_loc:
                self.last_known_location = baseline_loc.copy()
        except Exception:
            pass
        
        # Wait a moment before announcing first instruction to let route summary complete
        time.sleep(2)
        self._announce_current_instruction()
        
        last_instruction_check = time.time()
        last_reroute_check = time.time()
        
        while self.is_navigating:
            try:
                time.sleep(Config.NAVIGATION_UPDATE_INTERVAL)
                
                if not self.is_navigating:
                    break
                
                # Update simulated location if in simulation mode
                if self.simulation_mode:
                    self._update_simulated_location()
                
                current_time = time.time()
                
                # Check for auto-rerouting every 10 seconds
                if current_time - last_reroute_check >= 10.0:
                    last_reroute_check = current_time
                    if self._has_location_changed_significantly():
                        logger.debug("Checking for auto-rerouting due to location change")
                        self._check_and_reroute_if_needed()
                
                # Check waypoint arrival every 2 seconds
                if current_time - last_instruction_check >= 2.0:
                    last_instruction_check = current_time
                    
                    # Require recent movement to consider arrival at waypoint
                    moved_recently = (
                        self.last_movement_time is not None and
                        (current_time - self.last_movement_time) <= 6.0
                    )
                    if not moved_recently:
                        logger.debug("No recent movement; skipping arrival check")
                        continue
                    
                    distance_to_wp = self._distance_to_next_waypoint()
                    if distance_to_wp is not None:
                        logger.debug(f"Distance to next waypoint: {distance_to_wp:.1f}m (last={self._last_distance_to_waypoint})")
                        # Hysteresis: require previously far, now within threshold
                        previously_far = (
                            self._last_distance_to_waypoint is None or
                            self._last_distance_to_waypoint > (self.arrival_distance_threshold + self.arrival_hysteresis)
                        )
                        now_arrived = distance_to_wp <= self.arrival_distance_threshold
                        getting_closer = (
                            self._last_distance_to_waypoint is None or
                            distance_to_wp <= self._last_distance_to_waypoint - 2.0  # at least approaching by 2m
                        )
                        
                        # Only update last distance when movement is detected
                        if moved_recently:
                            self._last_distance_to_waypoint = distance_to_wp
                        
                        if previously_far and now_arrived and getting_closer:
                            # Increment arrival confirmation counter
                            self.arrival_confirmations += 1
                            logger.debug(f"Arrival confirmation {self.arrival_confirmations}/{self.required_arrival_confirmations} at {distance_to_wp:.1f}m")
                            
                            # Require multiple consecutive confirmations to prevent GPS drift false positives
                            if self.arrival_confirmations >= self.required_arrival_confirmations:
                                # Enforce minimum time between instructions
                                try:
                                    from datetime import datetime
                                    if self.last_instruction_time:
                                        elapsed = (datetime.now() - self.last_instruction_time).total_seconds()
                                        if elapsed < self.min_instruction_interval:
                                            logger.debug(f"Arrived but waiting min interval ({elapsed:.1f}s)")
                                            continue
                                except Exception:
                                    pass
                                
                                logger.info(f"✅ Confirmed arrival at waypoint (distance: {distance_to_wp:.1f}m) -> advancing to next instruction")
                                if self.navigation_service.advance_to_next_instruction():
                                    self.last_announced_instruction = None
                                    self._announce_current_instruction()
                                    # reset last-distance to require leaving new waypoint area
                                    self._last_distance_to_waypoint = None
                                    self.arrival_confirmations = 0  # Reset counter
                                else:
                                    self._handle_destination_reached()
                                    break
                        else:
                            # Not at waypoint or not getting closer - reset arrival counter
                            if self.arrival_confirmations > 0:
                                logger.debug(f"Resetting arrival confirmations (was {self.arrival_confirmations})")
                            self.arrival_confirmations = 0
                
            except Exception as e:
                logger.error(f"Error in navigation monitoring: {str(e)}")
                break
        
        logger.info("Navigation monitoring stopped")
    
    def _handle_destination_reached(self) -> None:
        """Handle reaching the destination"""
        try:
            self.is_navigating = False
            
            destination_name = self.current_destination['name'] if self.current_destination else "your destination"
            
            self.speech_service.speak(f"You have reached {destination_name}!")
            
            # Ask if user wants to save this location
            if self.current_destination:
                self.pending_save_location = self.current_destination
                self.speech_service.speak(
                    "Would you like to save this location to your favorites? Say 'yes' to save or 'no' to continue."
                )
            
        except Exception as e:
            logger.error(f"Error handling destination reached: {str(e)}")
    
    def _handle_repeat_instruction(self) -> None:
        """Handle repeat instruction request"""
        try:
            if not self.is_navigating:
                self.speech_service.speak("No active navigation to repeat.")
                return
            
            self._announce_current_instruction()
            
        except Exception as e:
            logger.error(f"Error repeating instruction: {str(e)}")
            self.speech_service.speak("Error repeating instruction.")
    
    def _handle_next_instruction(self) -> None:
        """Handle next instruction request"""
        try:
            if not self.is_navigating:
                self.speech_service.speak("No active navigation.")
                return
            
            if self.navigation_service.advance_to_next_instruction():
                self.last_announced_instruction = None  # Clear duplicate check for new instruction
                self._announce_current_instruction()
            else:
                self._handle_destination_reached()
            
        except Exception as e:
            logger.error(f"Error getting next instruction: {str(e)}")
            self.speech_service.speak("Error getting next instruction.")
    
    def _handle_current_location_request(self) -> None:
        """Handle current location request"""
        try:
            current_location = self.location_service.get_current_location()
            
            if not current_location:
                self.speech_service.speak("Current location not available. Please allow location access.")
                return
            
            address = self.location_service.reverse_geocode(
                current_location['lat'], 
                current_location['lng']
            )
            
            if address:
                self.speech_service.speak(f"You are currently at: {address}")
            else:
                self.speech_service.speak("Current location is available but address lookup failed.")
            
        except Exception as e:
            logger.error(f"Error getting current location: {str(e)}")
            self.speech_service.speak("Error getting current location.")
    
    def _handle_save_location_request(self) -> None:
        """Handle save location request"""
        try:
            if self.pending_save_location:
                # Save the pending location
                success = self.location_manager.add_favorite(self.pending_save_location)
                
                if success:
                    self.speech_service.speak(f"Saved {self.pending_save_location['name']} to favorites.")
                else:
                    self.speech_service.speak("This location is already in your favorites.")
                
                self.pending_save_location = None
                
            elif self.current_destination:
                # Save current destination
                success = self.location_manager.add_favorite(self.current_destination)
                
                if success:
                    self.speech_service.speak(f"Saved {self.current_destination['name']} to favorites.")
                else:
                    self.speech_service.speak("This location is already in your favorites.")
            else:
                self.speech_service.speak("No location to save.")
            
        except Exception as e:
            logger.error(f"Error saving location: {str(e)}")
            self.speech_service.speak("Error saving location.")
    
    def _handle_stop_navigation(self) -> None:
        """Handle stop navigation request"""
        try:
            if not self.is_navigating:
                self.speech_service.speak("No active navigation to stop.")
                return
            
            self._stop_navigation()
            self.speech_service.speak("Navigation stopped. Ready for new destination.")
            
        except Exception as e:
            logger.error(f"Error stopping navigation: {str(e)}")
            self.speech_service.speak("Error stopping navigation.")
    
    def _handle_clear_navigation(self) -> None:
        """Handle clear navigation state request"""
        try:
            logger.info("Clearing all navigation state")
            self._stop_navigation()  # This now clears everything
            self.speech_service.speak("Navigation cleared. Ready for new search.")
            
        except Exception as e:
            logger.error(f"Error clearing navigation: {str(e)}")
            self.speech_service.speak("Error clearing navigation.")
    
    def _stop_navigation(self) -> None:
        """Stop current navigation"""
        logger.info("Stopping navigation and clearing all state")
        self.is_navigating = False
        self.current_destination = None
        self.last_instruction_time = None
        self.last_announced_instruction = None
        self.last_known_location = None
        
        # Clear search state to allow new searches
        self.waiting_for_selection = False
        self.search_results = []
        
        # Clear navigation service state
        if hasattr(self, 'navigation_service'):
            self.navigation_service.current_route = None
            self.navigation_service.current_step_index = 0
        
        self.stop_location_simulation()  # Stop simulation if running
        
        if self.navigation_thread and self.navigation_thread.is_alive():
            self.navigation_thread.join(timeout=2)
        
        logger.info("Navigation state cleared completely")
    
    def _handle_simulation_command(self, command: Dict) -> None:
        """Handle location simulation command"""
        try:
            if not self.is_navigating:
                self.speech_service.speak("No active navigation to simulate.")
                return
            
            if self.simulation_mode:
                self.speech_service.speak("Location simulation is already running.", priority="low")
            else:
                self.start_location_simulation()
                # Use lower priority and shorter message to avoid interference
                self.speech_service.speak("Simulation started.", priority="low")
            
        except Exception as e:
            logger.error(f"Error handling simulation command: {str(e)}")
            self.speech_service.speak("Error starting location simulation.")
    
    def _handle_manual_advance_command(self, command: Dict) -> None:
        """Handle manual advance command for testing on real systems"""
        try:
            if not self.is_navigating:
                self.speech_service.speak("No active navigation.")
                return
            
            logger.info("Manual advance: simulating arrival at waypoint")
            # Manually trigger next instruction (like reaching a waypoint)
            if self.navigation_service.advance_to_next_instruction():
                self.last_announced_instruction = None
                self._announce_current_instruction()
            else:
                # Reached destination
                self._handle_destination_reached()
            
        except Exception as e:
            logger.error(f"Error handling manual advance command: {str(e)}")
            self.speech_service.speak("Error advancing navigation.")
    
    def manual_advance_instruction(self) -> bool:
        """
        Manually advance to the next instruction (for testing purposes)
        
        Returns:
            True if advanced successfully, False if at end of route
        """
        try:
            if not self.is_navigating:
                logger.warning("Cannot advance: no active navigation")
                return False
            
            if self.navigation_service.advance_to_next_instruction():
                self.last_announced_instruction = None
                self._announce_current_instruction()
                return True
            else:
                # Reached destination
                self._handle_destination_reached()
                return False
                
        except Exception as e:
            logger.error(f"Error in manual advance: {str(e)}")
            return False
    
    def _check_and_reroute_if_needed(self) -> None:
        """Check if user has deviated from route and reroute if necessary"""
        try:
            if not self.is_navigating or not self.current_destination:
                return
            
            current_location = self.location_service.get_current_location()
            if not current_location:
                return
            
            # Check if user is significantly off the current route
            if self._is_user_off_route(current_location):
                logger.info("User appears to be off route, auto-rerouting...")
                self.speech_service.speak("Recalculating route...", priority="high")
                
                # Get new route from current location to destination
                route = self.navigation_service.get_directions(
                    current_location, 
                    self.current_destination['location'], 
                    profile='foot'
                )
                
                if route:
                    # Update cache with new route
                    self.cache_service.cache_route(current_location, self.current_destination['location'], route)
                    
                    # Reset navigation state to beginning of new route
                    self.navigation_service.current_route = route
                    self.navigation_service.current_step_index = 0
                    self.last_announced_instruction = None
                    
                    # Announce new route
                    summary = self.navigation_service.get_route_summary(route)
                    if summary:
                        self.speech_service.speak(f"New route calculated. {summary}")
                    
                    # Announce first instruction of new route
                    self._announce_current_instruction()
                    
                    logger.info("Auto-reroute completed successfully")
                else:
                    logger.warning("Auto-reroute failed - could not calculate new route")
            
        except Exception as e:
            logger.error(f"Error in auto-rerouting: {str(e)}")
    
    def _is_user_off_route(self, current_location: Dict) -> bool:
        """Check if user is significantly off the current route"""
        try:
            if not self.navigation_service.current_route:
                return False
            
            # Get the next waypoint from current route
            next_waypoint = self._get_next_instruction_location()
            if not next_waypoint:
                return False
            
            # Calculate distance to next waypoint
            distance_to_waypoint = self._calculate_distance(
                current_location['lat'], current_location['lng'],
                next_waypoint['lat'], next_waypoint['lng']
            )
            
            # If user is more than 100 meters from the next waypoint, consider them off route
            off_route_threshold = 100.0  # meters
            is_off_route = distance_to_waypoint > off_route_threshold
            
            if is_off_route:
                logger.info(f"User is {distance_to_waypoint:.1f}m from next waypoint (threshold: {off_route_threshold}m)")
            
            return is_off_route
            
        except Exception as e:
            logger.error(f"Error checking if user is off route: {str(e)}")
            return False
    
    def _handle_reroute_command(self, command: Dict) -> None:
        """Handle manual reroute command for when user deviates from route"""
        try:
            if not self.is_navigating:
                self.speech_service.speak("No active navigation to reroute.")
                return
            
            if not self.current_destination:
                self.speech_service.speak("No destination set for rerouting.")
                return
            
            current_location = self.location_service.get_current_location()
            if not current_location:
                self.speech_service.speak("Current location not available for rerouting.")
                return
            
            logger.info("Manual rerouting from current location")
            self.speech_service.speak("Recalculating route...")
            
            # Get new route from current location to destination using current routing mode
            route = self.navigation_service.get_directions(current_location, self.current_destination['location'], profile=self.routing_mode)
            
            if route:
                # Update cache with new route
                self.cache_service.cache_route(current_location, self.current_destination['location'], route)
                
                # Reset navigation state to beginning of new route
                self.navigation_service.current_route = route
                self.navigation_service.current_step_index = 0
                self.last_announced_instruction = None
                
                # Announce new route
                summary = self.navigation_service.get_route_summary(route)
                if summary:
                    self.speech_service.speak(f"New route calculated. {summary}")
                
                # Announce first instruction of new route
                self._announce_current_instruction()
                
                logger.info("Manual reroute completed successfully")
            else:
                self.speech_service.speak("Unable to calculate new route. Continuing with original route.")
                logger.warning("Manual reroute failed - could not calculate new route")
            
        except Exception as e:
            logger.error(f"Error handling reroute command: {str(e)}")
            self.speech_service.speak("Error rerouting. Continuing with original route.")
    
    def _handle_help_request(self) -> None:
        """Handle help request"""
        try:
            help_text = self.speech_service.get_help_text()
            self.speech_service.speak(help_text)
            
        except Exception as e:
            logger.error(f"Error providing help: {str(e)}")
            self.speech_service.speak("Help information not available.")
    
    def _handle_unknown_command(self, command: Dict) -> None:
        """Handle unknown command"""
        self.speech_service.speak(
            f"I didn't understand '{command['raw_command']}'. "
            "Please try again or say 'help' for available commands."
        )
    
    def _handle_command_error(self, command: Dict) -> None:
        """Handle command processing error"""
        self.speech_service.speak(
            "Sorry, there was an error processing your command. Please try again."
        )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current application status
        
        Returns:
            Status dictionary
        """
        try:
            current_location = self.location_service.get_current_location()
            
            status = {
                'initialized': True,
                'is_navigating': self.is_navigating,
                'current_destination': self.current_destination['name'] if self.current_destination else None,
                'has_current_location': current_location is not None,
                'waiting_for_selection': self.waiting_for_selection,
                'search_results': self.search_results if self.waiting_for_selection else [],
                'pending_save_location': self.pending_save_location['name'] if self.pending_save_location else None,
                'cache_stats': self.cache_service.get_cache_stats(),
                'favorites_count': len(self.location_manager.get_favorites()),
                'last_update': datetime.now().isoformat()
            }
            
            # Include current location data if available
            if current_location:
                status['current_location'] = {
                    'lat': current_location['lat'],
                    'lng': current_location['lng']
                }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting status: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula
        
        Args:
            lat1, lng1: First coordinate
            lat2, lng2: Second coordinate
            
        Returns:
            Distance in meters
        """
        try:
            # Convert to radians
            lat1_rad = math.radians(lat1)
            lng1_rad = math.radians(lng1)
            lat2_rad = math.radians(lat2)
            lng2_rad = math.radians(lng2)
            
            # Haversine formula
            dlat = lat2_rad - lat1_rad
            dlng = lng2_rad - lng1_rad
            
            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            # Earth radius in meters
            earth_radius = 6371000
            distance = earth_radius * c
            
            return distance
            
        except Exception as e:
            logger.error(f"Error calculating distance: {str(e)}")
            return float('inf')
    
    def _get_next_instruction_location(self) -> Optional[Dict]:
        """
        Get the location coordinates for the next navigation instruction
        
        Returns:
            Dict with lat/lng of next waypoint or None
        """
        try:
            if not self.navigation_service.current_route:
                return None
            
            instructions = self.navigation_service.current_route.get('instructions', [])
            current_index = self.navigation_service.current_step_index
            
            if current_index >= len(instructions):
                return None
            
            # Try to get waypoint from the current instruction first
            current_instruction = instructions[current_index]
            if current_instruction and 'way_points' in current_instruction:
                way_points = current_instruction['way_points']
                if way_points and len(way_points) >= 2:
                    # way_points is [start_index, end_index] in the route geometry
                    geometry = self.navigation_service.current_route.get('geometry', {})
                    if geometry and 'coordinates' in geometry:
                        coordinates = geometry['coordinates']
                        # Use the end point of the current instruction
                        end_index = way_points[1]
                        if end_index < len(coordinates):
                            coord = coordinates[end_index]
                            return {'lat': coord[1], 'lng': coord[0]}  # OSRM uses [lng, lat]
            
            # Fallback to route waypoints
            waypoints = self.navigation_service.current_route.get('waypoints', [])
            
            if current_index < len(waypoints):
                waypoint = waypoints[min(current_index, len(waypoints) - 1)]
                location = waypoint.get('location', [])
                if len(location) >= 2:
                    return {'lat': location[1], 'lng': location[0]}  # OSRM uses [lng, lat]
            
            # Final fallback: use route geometry coordinates
            geometry = self.navigation_service.current_route.get('geometry', {})
            if geometry and 'coordinates' in geometry:
                coordinates = geometry['coordinates']
                # Use a point further along the route
                target_index = min(current_index * 10, len(coordinates) - 1)
                coord = coordinates[target_index]
                return {'lat': coord[1], 'lng': coord[0]}
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting next instruction location: {str(e)}")
            return None
    
    def _distance_to_next_waypoint(self) -> Optional[float]:
        """Compute distance in meters to the end of the current instruction."""
        try:
            current_location = self.location_service.get_current_location()
            if not current_location:
                return None
            next_waypoint = self._get_next_instruction_location()
            if not next_waypoint:
                return None
            return self._calculate_distance(
                current_location['lat'], current_location['lng'],
                next_waypoint['lat'], next_waypoint['lng']
            )
        except Exception as e:
            logger.error(f"Error computing distance to waypoint: {str(e)}")
            return None
    
    def _has_location_changed_significantly(self) -> bool:
        """
        Check if the user's location has changed significantly since last check
        
        Returns:
            True if location has changed by more than the threshold
        """
        try:
            current_location = self.location_service.get_current_location()
            if not current_location:
                return False
            
            if not self.last_known_location:
                # Set baseline without triggering a change to avoid immediate auto-advance
                self.last_known_location = current_location.copy()
                return False  # First time, do not consider it a change
            
            # Calculate distance moved since last check
            distance_moved = self._calculate_distance(
                self.last_known_location['lat'], self.last_known_location['lng'],
                current_location['lat'], current_location['lng']
            )
            
            logger.debug(f"Location change: {distance_moved:.1f}m (threshold: {self.location_change_threshold}m)")
            
            if distance_moved >= self.location_change_threshold:
                self.last_known_location = current_location.copy()
                try:
                    self.last_movement_time = time.time()
                except Exception:
                    pass
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking location change: {str(e)}")
            return False
    
    def start_location_simulation(self) -> None:
        """
        Start simulating GPS movement along the route for testing purposes
        """
        try:
            if not self.is_navigating or not self.navigation_service.current_route:
                logger.warning("Cannot start simulation: no active navigation")
                return
            
            self.simulation_mode = True
            self.last_simulation_update = time.time()
            logger.info("Started location simulation for testing navigation")
            
        except Exception as e:
            logger.error(f"Error starting location simulation: {str(e)}")
    
    def _update_simulated_location(self) -> None:
        """
        Update simulated GPS location moving along the route
        """
        try:
            if not self.simulation_mode or not self.is_navigating:
                return
            
            current_time = time.time()
            if not self.last_simulation_update:
                self.last_simulation_update = current_time
                return
            
            time_elapsed = current_time - self.last_simulation_update
            distance_moved = self.simulation_speed * time_elapsed  # meters
            
            current_location = self.location_service.get_current_location()
            next_waypoint = self._get_next_instruction_location()
            
            if current_location and next_waypoint:
                # Calculate direction to next waypoint
                current_distance = self._calculate_distance(
                    current_location['lat'], current_location['lng'],
                    next_waypoint['lat'], next_waypoint['lng']
                )
                
                if current_distance > 1.0:  # If more than 1 meter away
                    # Move towards the waypoint
                    fraction = min(distance_moved / current_distance, 1.0)
                    
                    new_lat = current_location['lat'] + fraction * (next_waypoint['lat'] - current_location['lat'])
                    new_lng = current_location['lng'] + fraction * (next_waypoint['lng'] - current_location['lng'])
                    
                    # Update location
                    self.location_service.set_current_location(new_lat, new_lng)
                    logger.debug(f"Simulated location updated to: {new_lat:.6f}, {new_lng:.6f}")
            
            self.last_simulation_update = current_time
            
        except Exception as e:
            logger.error(f"Error updating simulated location: {str(e)}")
    
    def stop_location_simulation(self) -> None:
        """
        Stop location simulation
        """
        self.simulation_mode = False
        logger.info("Stopped location simulation")
