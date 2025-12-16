import json
import logging
from typing import Optional
from django.conf import settings
from openai import OpenAI
from apps.domain.models import Document, DocumentAnalysis
from apps.infrastructure.services.pdf_extractor import PDFExtractorService

logger = logging.getLogger('apps')


class DocumentAnalysisService:
    def __init__(self, pdf_extractor: Optional[PDFExtractorService] = None):
        self.pdf_extractor = pdf_extractor or PDFExtractorService()
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    def analyze_document(self, document: Document, model: str = 'gpt-3.5-turbo') -> DocumentAnalysis:
        if not self.openai_client:
            raise ValueError('OpenAI API key is not configured')

        text = self.pdf_extractor.extract_text_from_url(document.file_url)
        
        if not text.strip():
            raise ValueError('No text could be extracted from the PDF')

        prompt = self._build_analysis_prompt(text)
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {'role': 'system', 'content': 'You are an expert document analyst. Analyze documents and provide structured insights.'},
                    {'role': 'user', 'content': prompt}
                ],
                temperature=0.7,
            )
            
            analysis_text = response.choices[0].message.content
            analysis_data = self._parse_analysis_response(analysis_text)
            
            analysis, created = DocumentAnalysis.objects.update_or_create(
                document=document,
                defaults={
                    'missing_topics': analysis_data.get('missing_topics', []),
                    'summary': analysis_data.get('summary', ''),
                    'insights': analysis_data.get('insights', {}),
                    'model_used': model,
                }
            )
            
            return analysis
        except Exception as e:
            logger.error(f'Error analyzing document {document.id} with OpenAI: {str(e)}')
            raise Exception(f'Failed to analyze document: {str(e)}')

    def _build_analysis_prompt(self, text: str) -> str:
        return f"""Analyze the following document and provide a structured analysis in JSON format.

Document text:
{text[:8000]}

Please provide your analysis in the following JSON format:
{{
    "missing_topics": ["topic1", "topic2", ...],
    "summary": "A brief summary of the document content",
    "insights": {{
        "key_points": ["point1", "point2", ...],
        "recommendations": ["recommendation1", "recommendation2", ...],
        "risks": ["risk1", "risk2", ...]
    }}
}}

Focus on:
- Missing important topics or clauses
- Key points and main content
- Recommendations for improvement
- Potential risks or concerns
"""

    def _parse_analysis_response(self, response_text: str) -> dict:
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning('Failed to parse JSON from OpenAI response, using fallback')
        
        return {
            'missing_topics': [],
            'summary': response_text[:500],
            'insights': {
                'key_points': [],
                'recommendations': [],
                'risks': []
            }
        }


