"""
Facade service that composes the services used by the Google-integrated
navigation flow. This keeps existing services untouched while exposing a
single, easy-to-consume API for the Google page and related endpoints.

This service does NOT replace existing controllers or routes; it merely wraps
them so callers can see which services are involved in one place.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from services.google_places_service import GooglePlacesService
from services.osm_navigation_service import OSMNavigationService
from services.location_service import LocationService

try:
    # Optional TTS; keep optional so this facade is non-invasive
    from services.improved_tts import ImprovedTTS as TTSService  # type: ignore
except Exception:  # pragma: no cover - optional
    TTSService = None  # type: ignore


class GoogleIntegratedNavigationService:
    """High-level facade for Google-integrated navigation workflow.

    Responsibilities:
    - Manage current location (via LocationService)
    - Search places using GooglePlacesService
    - Build routes and instructions using OSMNavigationService
    - Optionally speak instructions using TTSService (if available)
    """

    def __init__(
        self,
        *,
        google_api_key: Optional[str],
        profile: str = "foot",
    ) -> None:
        self.location_service = LocationService()
        self.places_service = GooglePlacesService(google_api_key) if google_api_key else None
        self.navigation_service = OSMNavigationService(profile=profile)
        self.tts = TTSService() if TTSService else None

        self._last_search_results: List[Dict[str, Any]] = []
        self._current_destination: Optional[Dict[str, Any]] = None
        self._current_route: Optional[Dict[str, Any]] = None

    # ---- Session / lifecycle -------------------------------------------------
    def start(self) -> Dict[str, Any]:
        return {"success": True, "message": "Facade ready"}

    def stop(self) -> Dict[str, Any]:
        self._current_destination = None
        self._current_route = None
        self._last_search_results = []
        return {"success": True, "message": "Stopped"}

    # ---- Location ------------------------------------------------------------
    def set_location(self, lat: float, lng: float) -> Dict[str, Any]:
        self.location_service.set_current_location(lat, lng)
        return {"success": True}

    def get_location(self) -> Optional[Tuple[float, float]]:
        loc = self.location_service.get_current_location()
        if not loc:
            return None
        return (loc["latitude"], loc["longitude"])  # type: ignore[index]

    # ---- Search / Selection --------------------------------------------------
    def search(self, query: str, *, radius: Optional[int] = None) -> Dict[str, Any]:
        if not self.places_service:
            return {"success": False, "message": "GOOGLE_MAPS_API_KEY not configured"}

        loc_tuple = self.get_location()
        location_dict = None
        if loc_tuple:
            location_dict = {"lat": loc_tuple[0], "lng": loc_tuple[1]}

        results = self.places_service.search_places(
            query=query, location=location_dict, radius=radius
        )
        self._last_search_results = results or []
        return {"success": True, "results": self._last_search_results}

    def select_result(self, index: int) -> Dict[str, Any]:
        if not (0 <= index < len(self._last_search_results)):
            return {"success": False, "message": "Invalid selection index"}
        self._current_destination = self._last_search_results[index]
        return {"success": True, "selected": self._current_destination}

    # ---- Navigation ----------------------------------------------------------
    def navigate_to_selected(self) -> Dict[str, Any]:
        if not self._current_destination:
            return {"success": False, "message": "No destination selected"}
        return self._build_route(self._current_destination)

    def navigate_to_place_id(self, place_id: str) -> Dict[str, Any]:
        if not self.places_service:
            return {"success": False, "message": "GOOGLE_MAPS_API_KEY not configured"}
        det = self.places_service.get_place_details(place_id)
        if not det:
            return {"success": False, "message": "place not found"}
        self._current_destination = det
        return self._build_route(det)

    def navigate_to_coordinates(self, *, name: str, lat: float, lng: float) -> Dict[str, Any]:
        place = {"name": name, "location": {"lat": lat, "lng": lng}}
        self._current_destination = place
        return self._build_route(place)

    def _build_route(self, place: Dict[str, Any]) -> Dict[str, Any]:
        origin = self.get_location()
        if not origin:
            return {"success": False, "message": "Current location not set"}

        dest_loc = place.get("location") or {}
        dest_lat = dest_loc.get("lat")
        dest_lng = dest_loc.get("lng")
        if dest_lat is None or dest_lng is None:
            return {"success": False, "message": "Destination missing lat/lng"}

        route = self.navigation_service.get_route(
            start_lat=origin[0], start_lng=origin[1], end_lat=dest_lat, end_lng=dest_lng
        )
        if not route or not route.get("geometry"):
            return {"success": False, "message": "No route available"}

        self._current_route = route
        return {"success": True, "route": route, "destination": place.get("name")}

    # ---- Info / Status -------------------------------------------------------
    def get_route(self) -> Dict[str, Any]:
        if not self._current_route:
            return {"success": False, "message": "No active route"}
        return {"success": True, "route": self._current_route}

    def get_unified_instruction(self) -> Dict[str, Any]:
        if not self._current_route:
            return {"success": False, "message": "No active route"}

        instr = self.navigation_service.get_current_instruction(self._current_route)
        if not instr:
            return {"success": False, "message": "No instruction"}

        if self.tts and instr.get("speech_instruction"):
            try:
                self.tts.speak(instr["speech_instruction"])  # type: ignore[index]
            except Exception:
                pass

        return {"success": True, "instruction": instr}


