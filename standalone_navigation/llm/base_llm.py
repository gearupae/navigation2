"""
Base LLM Interface - Abstract base class for all LLM implementations
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class BaseLLM(ABC):
    """Abstract base class for Language Model implementations"""
    
    def __init__(self, api_key: str, model: str = None):
        """
        Initialize the LLM
        
        Args:
            api_key: API key for the LLM service
            model: Model name/version to use
        """
        self.api_key = api_key
        self.model = model
        self.logger = logger
    
    @abstractmethod
    def analyze_image(self, image_data: bytes, prompt: str = None) -> Dict[str, Any]:
        """
        Analyze an image and return structured results
        
        Args:
            image_data: Image data as bytes
            prompt: Optional custom prompt
            
        Returns:
            Dictionary with analysis results including:
            - narration: str - Human-readable description
            - hazards: List[str] - List of detected hazards
            - suggested_heading: str - Suggested direction
            - confidence: float - Confidence score
        """
        pass
    
    @abstractmethod
    def generate_text(self, prompt: str, max_tokens: int = 150) -> str:
        """
        Generate text based on prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        pass
    
    @abstractmethod
    def improve_narration(self, instruction: str, context: str = None) -> str:
        """
        Improve navigation instruction for better accessibility
        
        Args:
            instruction: Original instruction
            context: Additional context (optional)
            
        Returns:
            Improved instruction
        """
        pass
    
    def get_default_vision_prompt(self) -> str:
        """
        Get default prompt for vision analysis
        
        Returns:
            Default prompt string
        """
        return """
        Analyze this image for outdoor navigation assistance. Focus on:
        1. Obstacles and hazards that could affect walking
        2. Clear paths and safe directions
        3. Important landmarks or navigation cues
        
        Provide a brief, actionable description in 15 words or less.
        If obstacles are detected, suggest a clear steering direction (left, right, straight).
        """
    
    def get_default_narration_prompt(self) -> str:
        """
        Get default prompt for narration improvement
        
        Returns:
            Default prompt string
        """
        return """
        Improve this navigation instruction for blind users:
        - Use tactile and actionable language
        - Avoid visual references like "watch" or "look"
        - Provide clear, step-by-step guidance
        - Use distance in steps (1 step = 0.7 meters)
        - Be specific about turns and directions
        
        Keep it under 20 words and make it immediately actionable.
        """
    
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate LLM response format
        
        Args:
            response: Response dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['narration']
        return all(field in response for field in required_fields)
    
    def format_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format and standardize LLM response
        
        Args:
            response: Raw response dictionary
            
        Returns:
            Formatted response dictionary
        """
        formatted = {
            'narration': response.get('narration', ''),
            'hazards': response.get('hazards', []),
            'suggested_heading': response.get('suggested_heading', 'straight'),
            'confidence': response.get('confidence', 0.8),
            'provider': self.__class__.__name__
        }
        
        # Ensure hazards is a list
        if not isinstance(formatted['hazards'], list):
            formatted['hazards'] = []
        
        return formatted



