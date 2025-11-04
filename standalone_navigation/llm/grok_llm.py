"""
Grok LLM Implementation - X.AI Grok Vision API
"""
import requests
import base64
import json
from typing import Dict, List, Optional, Any
from .base_llm import BaseLLM

class GrokLLM(BaseLLM):
    """Grok LLM implementation for vision analysis and text generation"""
    
    def __init__(self, api_key: str, model: str = "grok-beta"):
        """
        Initialize Grok LLM
        
        Args:
            api_key: X.AI API key
            model: Model name (default: grok-beta)
        """
        super().__init__(api_key, model)
        self.base_url = "https://api.x.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def analyze_image(self, image_data: bytes, prompt: str = None) -> Dict[str, Any]:
        """
        Analyze image using Grok Vision API
        
        Args:
            image_data: Image data as bytes
            prompt: Optional custom prompt
            
        Returns:
            Analysis results dictionary
        """
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Use default prompt if none provided
            if not prompt:
                prompt = self.get_default_vision_prompt()
            
            # Prepare request payload
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 150,
                "temperature": 0.3
            }
            
            # Make API request
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            # Parse the response to extract structured data
            result = self._parse_vision_response(content)
            
            return self.format_response(result)
            
        except Exception as e:
            self.logger.error(f"Grok vision analysis error: {e}")
            return self.format_response({
                'narration': 'Unable to analyze image',
                'hazards': [],
                'suggested_heading': 'straight',
                'confidence': 0.0
            })
    
    def generate_text(self, prompt: str, max_tokens: int = 150) -> str:
        """
        Generate text using Grok API
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data['choices'][0]['message']['content']
            
        except Exception as e:
            self.logger.error(f"Grok text generation error: {e}")
            return "Unable to generate text"
    
    def improve_narration(self, instruction: str, context: str = None) -> str:
        """
        Improve navigation instruction using Grok
        
        Args:
            instruction: Original instruction
            context: Additional context
            
        Returns:
            Improved instruction
        """
        try:
            prompt = f"""
            {self.get_default_narration_prompt()}
            
            Original instruction: "{instruction}"
            {f"Context: {context}" if context else ""}
            
            Provide the improved instruction:
            """
            
            return self.generate_text(prompt, max_tokens=50)
            
        except Exception as e:
            self.logger.error(f"Grok narration improvement error: {e}")
            return instruction
    
    def _parse_vision_response(self, content: str) -> Dict[str, Any]:
        """
        Parse Grok vision response to extract structured data
        
        Args:
            content: Raw response content
            
        Returns:
            Structured response dictionary
        """
        # Default response
        result = {
            'narration': content,
            'hazards': [],
            'suggested_heading': 'straight',
            'confidence': 0.8
        }
        
        # Try to extract hazards
        content_lower = content.lower()
        hazard_keywords = ['obstacle', 'hazard', 'danger', 'blocked', 'barrier', 'wall', 'car', 'vehicle']
        
        for keyword in hazard_keywords:
            if keyword in content_lower:
                result['hazards'].append(keyword)
        
        # Try to extract direction
        direction_keywords = {
            'left': ['left', 'turn left', 'go left'],
            'right': ['right', 'turn right', 'go right'],
            'straight': ['straight', 'continue', 'forward', 'ahead']
        }
        
        for direction, keywords in direction_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                result['suggested_heading'] = direction
                break
        
        return result






