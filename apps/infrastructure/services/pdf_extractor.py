import requests
import logging
import io
from typing import Optional

logger = logging.getLogger('apps')


class PDFExtractorService:
    def extract_text_from_url(self, url: str) -> str:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            pdf_file = io.BytesIO(response.content)
            return self._extract_text_from_bytes(pdf_file)
        except requests.exceptions.RequestException as e:
            logger.error(f'Error downloading PDF from URL {url}: {str(e)}')
            raise Exception(f'Failed to download PDF from URL: {str(e)}')
        except Exception as e:
            logger.error(f'Error extracting text from PDF: {str(e)}')
            raise Exception(f'Failed to extract text from PDF: {str(e)}')

    def extract_text_from_bytes(self, pdf_bytes: io.BytesIO) -> str:
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(pdf_bytes) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return '\n\n'.join(text_parts)
        except ImportError:
            logger.warning('pdfplumber não está instalado. Instale com: pip install pdfplumber')
            raise Exception('pdfplumber is not installed. Cannot extract text from PDF.')
        except Exception as e:
            logger.error(f'Error extracting text from PDF bytes: {str(e)}')
            raise Exception(f'Failed to extract text from PDF bytes: {str(e)}')


