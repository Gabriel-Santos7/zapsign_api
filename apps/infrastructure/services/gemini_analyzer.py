import json
import logging
from typing import Dict, Optional
from django.conf import settings

logger = logging.getLogger('apps')

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning('google-generativeai not installed. Install with: pip install google-generativeai')


class GeminiAPIError(Exception):
    """Base exception for Gemini API errors"""
    pass


class GeminiRateLimitError(GeminiAPIError):
    """Raised when rate limit is exceeded"""
    pass


class GeminiTimeoutError(GeminiAPIError):
    """Raised when request times out"""
    pass


class GeminiParseError(GeminiAPIError):
    """Raised when JSON parsing fails"""
    pass


class GeminiAnalyzerService:
    def __init__(self):
        if not GEMINI_AVAILABLE:
            raise ImportError('google-generativeai is not installed. Install with: pip install google-generativeai')
        
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError('GEMINI_API_KEY not configured in settings')
        
        # Configure Gemini API - API key sempre do settings (que lê do .env)
        genai.configure(api_key=api_key)
        
        self.model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-3-flash-preview')
        self.max_text_length = getattr(settings, 'GEMINI_MAX_TEXT_LENGTH', 50000)
        self.timeout = getattr(settings, 'GEMINI_TIMEOUT', 30)
        
        try:
            # Try to initialize the model
            self.model = genai.GenerativeModel(self.model_name)
            # Test if model is available by checking if it can be listed
            logger.info(f'Initialized Gemini model: {self.model_name}')
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Error initializing Gemini model {self.model_name}: {error_msg}')
            # If model not found, suggest alternatives
            if 'not found' in error_msg.lower() or '404' in error_msg:
                logger.warning(f'Model {self.model_name} not found. Available models: gemini-pro, gemini-1.5-pro, gemini-3-flash-preview')
                raise GeminiAPIError(f'Gemini model {self.model_name} not found. Try: gemini-pro, gemini-1.5-pro, or gemini-3-flash-preview')
            raise GeminiAPIError(f'Failed to initialize Gemini model: {error_msg}')
    
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze text using Gemini API and return structured analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with keys: summary, missing_topics, insights
            
        Raises:
            GeminiRateLimitError: When rate limit is exceeded
            GeminiTimeoutError: When request times out
            GeminiParseError: When JSON parsing fails
            GeminiAPIError: For other API errors
        """
        # Truncate text to save tokens
        truncated_text = text[:self.max_text_length]
        if len(text) > self.max_text_length:
            logger.info(f'Text truncated from {len(text)} to {self.max_text_length} characters')
        
        # Create prompt in English (responses in Portuguese)
        prompt = self._create_analysis_prompt(truncated_text)
        
        try:
            # Generate response with JSON format
            generation_config = {
                'temperature': 0.3,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 2048,
            }
            
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config,
                )
            except Exception as api_error:
                # Check for rate limit or quota errors
                error_str = str(api_error).lower()
                if '429' in error_str or 'rate limit' in error_str or 'quota' in error_str or 'resource_exhausted' in error_str:
                    logger.warning('Gemini rate limit reached, falling back to spaCy')
                    raise GeminiRateLimitError('Gemini API rate limit exceeded')
                elif 'timeout' in error_str or 'timed out' in error_str:
                    logger.warning(f'Gemini request timed out after {self.timeout}s')
                    raise GeminiTimeoutError(f'Gemini API request timed out')
                else:
                    raise
            
            # Extract text from response
            if not response.text:
                raise GeminiAPIError('Empty response from Gemini API')
            
            response_text = response.text.strip()
            
            # Try to parse as JSON
            try:
                # Remove markdown code blocks if present
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                analysis_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f'Failed to parse Gemini JSON response: {str(e)}')
                logger.debug(f'Response text: {response_text[:500]}')
                raise GeminiParseError(f'Invalid JSON response from Gemini: {str(e)}')
            
            # Validate and structure response
            return self._structure_response(analysis_data, response)
            
        except (GeminiRateLimitError, GeminiTimeoutError, GeminiParseError):
            # Re-raise specific errors
            raise
        except Exception as e:
            # Check for specific error types
            error_str = str(e).lower()
            
            if '429' in error_str or 'rate limit' in error_str or 'quota' in error_str or 'resource_exhausted' in error_str:
                logger.warning('Gemini rate limit reached, falling back to spaCy')
                raise GeminiRateLimitError('Gemini API rate limit exceeded')
            elif 'timeout' in error_str or 'timed out' in error_str:
                logger.warning(f'Gemini request timed out after {self.timeout}s')
                raise GeminiTimeoutError(f'Gemini API request timed out')
            else:
                logger.error(f'Gemini API error: {str(e)}')
                # Never expose API key in error messages
                raise GeminiAPIError(f'Gemini API error occurred')
    
    def _create_analysis_prompt(self, text: str) -> str:
        """Create analysis prompt in English (responses in Portuguese)"""
        return f"""Analyze the following document in Portuguese and provide a structured JSON response.

Document text (first {self.max_text_length} characters):
{text}

Provide a JSON response with the following structure:
{{
  "summary": "Executive summary in Portuguese (3-5 sentences)",
  "missing_topics": ["Topic 1", "Topic 2", ...],
  "insights": {{
    "key_points": ["Point 1", "Point 2", ...],
    "recommendations": ["Recommendation 1", ...],
    "risks": ["Risk 1", "Risk 2", ...],
    "obligations_and_rights": ["Obligation/Right 1", ...]
  }}
}}

Important:
- All text must be in Portuguese
- missing_topics should identify important topics that may be missing (legal/contractual context)
- key_points should be the most important points from the document
- recommendations should be contextual suggestions based on document completeness
- risks should identify potential legal or business risks
- obligations_and_rights should identify obligations and rights mentioned
- Return ONLY valid JSON, no markdown, no explanations, no code blocks
- Maximum 10 items per array
"""
    
    def _structure_response(self, analysis_data: Dict, response) -> Dict:
        """Structure and validate Gemini response"""
        # Extract tokens used if available
        tokens_used = None
        if hasattr(response, 'usage_metadata'):
            tokens_used = getattr(response.usage_metadata, 'total_token_count', None)
        
        # Ensure all required fields exist
        result = {
            'summary': analysis_data.get('summary', ''),
            'missing_topics': analysis_data.get('missing_topics', [])[:10],
            'insights': {
                'key_points': analysis_data.get('insights', {}).get('key_points', [])[:10],
                'recommendations': analysis_data.get('insights', {}).get('recommendations', [])[:5],
                'risks': analysis_data.get('insights', {}).get('risks', [])[:5],
                'obligations_and_rights': analysis_data.get('insights', {}).get('obligations_and_rights', [])[:3],
            },
            'tokens_used': tokens_used,
        }
        
        return result

