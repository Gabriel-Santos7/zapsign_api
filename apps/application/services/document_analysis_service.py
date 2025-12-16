import logging
import re
from typing import Optional, List, Dict
from collections import Counter
import spacy
from apps.domain.models import Document, DocumentAnalysis
from apps.infrastructure.services.pdf_extractor import PDFExtractorService

logger = logging.getLogger('apps')


class DocumentAnalysisService:
    _nlp_model = None
    
    def __init__(self, pdf_extractor: Optional[PDFExtractorService] = None):
        self.pdf_extractor = pdf_extractor or PDFExtractorService()

    @property
    def nlp(self):
        if DocumentAnalysisService._nlp_model is None:
            try:
                DocumentAnalysisService._nlp_model = spacy.load('pt_core_news_sm')
            except OSError:
                logger.warning('spaCy Portuguese model not found. Please run: python -m spacy download pt_core_news_sm')
                try:
                    DocumentAnalysisService._nlp_model = spacy.load('en_core_web_sm')
                    logger.warning('Using English model as fallback')
                except OSError:
                    logger.error('No spaCy model available. Please install a model.')
                    DocumentAnalysisService._nlp_model = False
        return DocumentAnalysisService._nlp_model if DocumentAnalysisService._nlp_model else None

    def analyze_document(self, document: Document, model: str = 'spacy') -> DocumentAnalysis:
        nlp_model = self.nlp
        if not nlp_model:
            raise ValueError('spaCy model is not configured. Please install a model: python -m spacy download pt_core_news_sm')

        text = self.pdf_extractor.extract_text_from_url(document.file_url)
        
        if not text.strip():
            raise ValueError('No text could be extracted from the PDF')

        try:
            analysis_data = self._analyze_with_spacy(text)
            
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
            logger.error(f'Error analyzing document {document.id} with spaCy: {str(e)}')
            raise Exception(f'Failed to analyze document: {str(e)}')

    def _analyze_with_spacy(self, text: str) -> Dict:
        nlp_model = self.nlp
        if not nlp_model:
            raise ValueError('spaCy model is not available')
        doc = nlp_model(text[:100000])
        
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        entities = {}
        for ent in doc.ents:
            if ent.label_ not in entities:
                entities[ent.label_] = []
            entities[ent.label_].append(ent.text)
        
        key_nouns = self._extract_key_nouns(doc)
        
        summary = self._generate_summary(sentences)
        
        missing_topics = self._identify_missing_topics(doc, text)
        
        key_points = self._extract_key_points(sentences, key_nouns)
        
        recommendations = self._generate_recommendations(doc, text)
        
        risks = self._identify_risks(doc, text)
        
        return {
            'missing_topics': missing_topics,
            'summary': summary,
            'insights': {
                'key_points': key_points,
                'recommendations': recommendations,
                'risks': risks,
                'entities': {k: list(set(v[:10])) for k, v in entities.items()}
            }
        }

    def _extract_key_nouns(self, doc) -> List[str]:
        noun_phrases = []
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) >= 2:
                noun_phrases.append(chunk.text.lower())
        
        counter = Counter(noun_phrases)
        return [phrase for phrase, count in counter.most_common(15)]

    def _generate_summary(self, sentences: List[str]) -> str:
        if not sentences:
            return ''
        
        if len(sentences) <= 3:
            return ' '.join(sentences)
        
        summary_length = min(3, len(sentences) // 3)
        summary_sentences = sentences[:summary_length] + sentences[-summary_length:] if len(sentences) > summary_length * 2 else sentences[:summary_length]
        
        return ' '.join(summary_sentences[:500])

    def _identify_missing_topics(self, doc, text: str) -> List[str]:
        common_topics = [
            'data', 'prazo', 'prazo de', 'validade', 'vigência',
            'valor', 'preço', 'pagamento', 'forma de pagamento',
            'responsabilidade', 'obrigações', 'direitos',
            'rescisão', 'cancelamento', 'término',
            'confidencialidade', 'sigilo',
            'multa', 'penalidade', 'indenização',
            'foro', 'jurisdição', 'lei aplicável'
        ]
        
        text_lower = text.lower()
        missing = []
        
        for topic in common_topics:
            if topic not in text_lower:
                missing.append(topic.title())
        
        return missing[:10]

    def _extract_key_points(self, sentences: List[str], key_nouns: List[str]) -> List[str]:
        key_points = []
        
        for sentence in sentences[:20]:
            sentence_lower = sentence.lower()
            for noun in key_nouns[:5]:
                if noun in sentence_lower and len(sentence) > 20:
                    key_points.append(sentence[:200])
                    break
        
        return key_points[:10]

    def _generate_recommendations(self, doc, text: str) -> List[str]:
        recommendations = []
        
        if 'assinatura' not in text.lower() and 'signatário' not in text.lower():
            recommendations.append('Considerar adicionar informações sobre signatários')
        
        if 'data' not in text.lower() and 'dia' not in text.lower():
            recommendations.append('Adicionar datas importantes ao documento')
        
        if len(text) < 500:
            recommendations.append('Documento pode ser expandido com mais detalhes')
        
        if not re.search(r'\d+', text):
            recommendations.append('Considerar adicionar valores numéricos quando aplicável')
        
        return recommendations[:5]

    def _identify_risks(self, doc, text: str) -> List[str]:
        risks = []
        text_lower = text.lower()
        
        risk_keywords = {
            'multa': 'Verificar cláusulas de multa',
            'rescisão': 'Revisar termos de rescisão',
            'confidencialidade': 'Confirmar cláusulas de confidencialidade',
            'indenização': 'Avaliar cláusulas de indenização',
            'jurisdição': 'Verificar foro e jurisdição aplicável'
        }
        
        for keyword, risk_msg in risk_keywords.items():
            if keyword in text_lower:
                risks.append(risk_msg)
        
        if not risks:
            risks.append('Documento parece estar em formato básico, considerar revisão jurídica')
        
        return risks[:5]


