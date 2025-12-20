import requests
import logging
import io
from typing import Optional

logger = logging.getLogger('apps')


class PDFExtractorService:
    def extract_text_from_url(self, url: str) -> str:
        try:
            # Add headers to avoid 403 Forbidden errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/pdf,application/octet-stream,*/*',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            
            response = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
            
            # Check status code and provide specific error messages
            if response.status_code == 403:
                error_msg = f'Access forbidden (403) when downloading PDF from URL. The server may be blocking automated requests.'
                logger.error(f'{error_msg} URL: {url}')
                raise ValueError(error_msg)
            elif response.status_code == 404:
                error_msg = f'PDF not found (404) at URL: {url}'
                logger.error(error_msg)
                raise ValueError(error_msg)
            elif response.status_code == 401:
                error_msg = f'Unauthorized (401) when downloading PDF from URL. Authentication may be required.'
                logger.error(f'{error_msg} URL: {url}')
                raise ValueError(error_msg)
            
            response.raise_for_status()
            
            # Check if response is actually a PDF
            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                logger.warning(f'Content-Type is {content_type}, but proceeding with extraction. URL: {url}')
            
            pdf_file = io.BytesIO(response.content)
            return self.extract_text_from_bytes(pdf_file)
        except requests.exceptions.Timeout:
            error_msg = f'Timeout when downloading PDF from URL: {url}'
            logger.error(error_msg)
            raise ValueError(error_msg)
        except requests.exceptions.ConnectionError as e:
            error_msg = f'Connection error when downloading PDF from URL: {url}'
            logger.error(f'{error_msg} - {str(e)}')
            raise ValueError(f'{error_msg}. Please check if the URL is accessible.')
        except requests.exceptions.RequestException as e:
            error_msg = f'Error downloading PDF from URL: {url}'
            logger.error(f'{error_msg} - {str(e)}')
            raise ValueError(f'{error_msg}. Status: {getattr(e.response, "status_code", "unknown")}')
        except ValueError:
            # Re-raise ValueError as-is (already has user-friendly message)
            raise
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


