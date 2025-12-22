import logging
import re
import time
from typing import Optional, List, Dict
from collections import Counter
from django.conf import settings
from apps.domain.models import Document, DocumentAnalysis
from apps.infrastructure.services.pdf_extractor import PDFExtractorService
from apps.infrastructure.services.gemini_analyzer import (
    GeminiAnalyzerService,
    GeminiAPIError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiParseError
)

logger = logging.getLogger('apps')


class DocumentAnalysisService:
    _nlp_model = None
    
    def __init__(self, pdf_extractor: Optional[PDFExtractorService] = None):
        self.pdf_extractor = pdf_extractor or PDFExtractorService()

    @property
    def nlp(self):
        if DocumentAnalysisService._nlp_model is None:
            try:
                import spacy
                import subprocess
                import sys
                
                # Try to load preferred model from settings, fallback to smaller model
                preferred_model = getattr(settings, 'SPACY_MODEL', 'pt_core_news_lg')
                
                def try_load_model(model_name: str) -> bool:
                    """Tenta carregar um modelo, retorna True se sucesso"""
                    try:
                        DocumentAnalysisService._nlp_model = spacy.load(model_name)
                        logger.info(f'Loaded spaCy model: {model_name}')
                        return True
                    except OSError:
                        return False
                
                def try_download_model(model_name: str) -> bool:
                    """Tenta baixar um modelo, retorna True se sucesso"""
                    try:
                        logger.info(f'Attempting to download spaCy model: {model_name}')
                        subprocess.check_call([
                            sys.executable, '-m', 'spacy', 'download', model_name
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        logger.info(f'Successfully downloaded spaCy model: {model_name}')
                        return True
                    except (subprocess.CalledProcessError, Exception) as e:
                        logger.warning(f'Failed to download spaCy model {model_name}: {str(e)}')
                        return False
                
                # Tenta carregar modelo preferido
                if try_load_model(preferred_model):
                    pass  # Sucesso
                # Se falhar, tenta baixar o modelo preferido
                elif try_download_model(preferred_model) and try_load_model(preferred_model):
                    pass  # Baixou e carregou com sucesso
                # Se ainda falhar, tenta modelo menor
                elif try_load_model('pt_core_news_sm'):
                    pass  # Sucesso com modelo menor
                # Se falhar, tenta baixar modelo menor
                elif try_download_model('pt_core_news_sm') and try_load_model('pt_core_news_sm'):
                    pass  # Baixou e carregou modelo menor
                # Último recurso: modelo em inglês
                elif try_load_model('en_core_web_sm'):
                    logger.warning('Using English model as fallback')
                # Tenta baixar modelo em inglês
                elif try_download_model('en_core_web_sm') and try_load_model('en_core_web_sm'):
                    logger.warning('Downloaded and using English model as fallback')
                else:
                    logger.error('No spaCy model available. Analysis will not work.')
                    DocumentAnalysisService._nlp_model = False
                    
            except ImportError:
                logger.warning('spaCy is not installed. Please install with: pip install spacy')
                DocumentAnalysisService._nlp_model = False
        return DocumentAnalysisService._nlp_model if DocumentAnalysisService._nlp_model else None

    def analyze_document(self, document: Document, model: str = 'auto') -> DocumentAnalysis:
        start_time = time.time()
        text = self.pdf_extractor.extract_text_from_url(document.file_url)
        
        if not text.strip():
            raise ValueError('No text could be extracted from the PDF')

        provider_used = 'spacy'
        fallback_reason = None
        analysis_data = None
        gemini_tokens_used = None
        gemini_model = None
        
        # Try Gemini first if enabled and API key is configured
        gemini_enabled = getattr(settings, 'GEMINI_ENABLED', True)
        gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
        
        if gemini_enabled and gemini_api_key and model != 'spacy':
            try:
                logger.info(f'Attempting to analyze document {document.id} with Gemini')
                gemini_service = GeminiAnalyzerService()
                gemini_result = gemini_service.analyze_text(text)
                
                # Convert Gemini result to expected format
                analysis_data = {
                    'missing_topics': gemini_result.get('missing_topics', []),
                    'summary': gemini_result.get('summary', ''),
                    'insights': gemini_result.get('insights', {}),
                    'sentences': [],  # Gemini doesn't provide sentences
                }
                
                provider_used = 'gemini'
                gemini_tokens_used = gemini_result.get('tokens_used')
                gemini_model = getattr(settings, 'GEMINI_MODEL', 'gemini-3-flash-preview')
                
                logger.info(f'Successfully analyzed document {document.id} with Gemini')
                
            except GeminiRateLimitError as e:
                logger.warning(f'Gemini rate limit reached for document {document.id}, falling back to spaCy')
                fallback_reason = 'rate_limit'
            except GeminiTimeoutError as e:
                logger.warning(f'Gemini timeout for document {document.id}, falling back to spaCy')
                fallback_reason = 'timeout'
            except (GeminiParseError, GeminiAPIError) as e:
                logger.warning(f'Gemini API error for document {document.id}: {str(e)}, falling back to spaCy')
                fallback_reason = 'api_error'
            except Exception as e:
                logger.warning(f'Unexpected error with Gemini for document {document.id}: {str(e)}, falling back to spaCy')
                fallback_reason = 'unexpected_error'
        
        # Fallback to spaCy if Gemini wasn't used or failed
        if not analysis_data:
            if provider_used == 'spacy' and not gemini_api_key:
                logger.info(f'Gemini API key not configured, using spaCy for document {document.id}')
                fallback_reason = 'not_configured'
            
            nlp_model = self.nlp
            if not nlp_model:
                raise ValueError('spaCy model is not configured. Please install a model: python -m spacy download pt_core_news_sm')
            
            try:
                analysis_data = self._analyze_with_spacy(text)
                provider_used = 'spacy'
            except Exception as e:
                logger.error(f'Error analyzing document {document.id} with spaCy: {str(e)}')
                raise Exception(f'Failed to analyze document: {str(e)}')
        
        processing_time = time.time() - start_time
        
        # Get model name for metadata
        model_name = 'unknown'
        if provider_used == 'spacy':
            nlp_model = self.nlp
            if nlp_model:
                model_name = nlp_model.meta.get('name', 'spacy')
        else:
            model_name = gemini_model or 'gemini-3-flash-preview'
        
        # Prepare metadata
        metadata = {
            'processing_time_seconds': round(processing_time, 2),
            'model_name': model_name,
            'provider_used': provider_used,
            'algorithm_version': '2.0'
        }
        
        if provider_used == 'gemini':
            if gemini_tokens_used:
                metadata['gemini_tokens_used'] = gemini_tokens_used
            if gemini_model:
                metadata['gemini_model'] = gemini_model
        else:
            metadata['sentences_analyzed'] = len(analysis_data.get('sentences', []))
        
        if fallback_reason:
            metadata['fallback_reason'] = fallback_reason
        
        analysis, created = DocumentAnalysis.objects.update_or_create(
            document=document,
            defaults={
                'missing_topics': analysis_data.get('missing_topics', []),
                'summary': analysis_data.get('summary', ''),
                'insights': analysis_data.get('insights', {}),
                'model_used': provider_used,
                'analysis_metadata': metadata,
            }
        )
        
        return analysis

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
        
        # Improved summary with sentence scoring
        summary = self._generate_summary_improved(sentences, doc)
        
        # Improved missing topics with semantic analysis
        missing_topics = self._identify_missing_topics_improved(doc, text)
        
        # Improved insights
        key_points = self._extract_key_points_improved(sentences, key_nouns, doc)
        recommendations = self._generate_recommendations_improved(doc, text)
        risks = self._identify_risks_improved(doc, text)
        obligations_and_rights = self._extract_obligations_and_rights(doc)
        
        return {
            'missing_topics': missing_topics,
            'summary': summary,
            'sentences': sentences,  # Store for metadata
            'insights': {
                'key_points': key_points,
                'recommendations': recommendations,
                'risks': risks,
                'obligations_and_rights': obligations_and_rights,
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
        """Legacy method - kept for backward compatibility"""
        if not sentences:
            return ''
        
        if len(sentences) <= 3:
            return ' '.join(sentences)
        
        summary_length = min(3, len(sentences) // 3)
        summary_sentences = sentences[:summary_length] + sentences[-summary_length:] if len(sentences) > summary_length * 2 else sentences[:summary_length]
        
        return ' '.join(summary_sentences[:500])
    
    def _generate_summary_improved(self, sentences: List[str], doc) -> str:
        """Improved summary using sentence importance scoring"""
        if not sentences:
            return ''
        
        if len(sentences) <= 3:
            return ' '.join(sentences)
        
        summary_length = getattr(settings, 'ANALYSIS_SUMMARY_LENGTH', 5)
        
        # Calculate importance score for each sentence
        sentence_scores = []
        for i, sent_text in enumerate(sentences):
            score = 0
            
            # Find the sentence span in the doc
            sent_span = None
            for sent in doc.sents:
                if sent.text.strip() == sent_text:
                    sent_span = sent
                    break
            
            if sent_span:
                # Score based on entities in sentence
                entities_in_sent = [e for e in doc.ents if e.sent == sent_span]
                score += len(entities_in_sent) * 2
                
                # Score based on key nouns/phrases
                key_terms = ['prazo', 'valor', 'contrato', 'responsabilidade', 'obrigação', 
                            'direito', 'prazo de', 'data', 'vencimento', 'pagamento']
                sent_lower = sent_text.lower()
                for term in key_terms:
                    if term in sent_lower:
                        score += 1
                
                # Score based on position (beginning and end are more important)
                if i < 3 or i > len(sentences) - 3:
                    score += 1
                
                # Score based on sentence length (ideal: 20-200 chars)
                if 20 < len(sent_text) < 200:
                    score += 1
                elif len(sent_text) < 20:
                    score -= 1  # Too short sentences are less important
                
                # Score based on numbers (sentences with numbers are often important)
                if re.search(r'\d+', sent_text):
                    score += 1
            
            sentence_scores.append((sent_text, score, i))
        
        # Sort by score and select top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = sentence_scores[:summary_length]
        
        # Sort selected sentences by original position to maintain coherence
        top_sentences.sort(key=lambda x: x[2])
        
        summary = ' '.join([s[0] for s in top_sentences])
        
        # Limit total length
        if len(summary) > 500:
            summary = summary[:497] + '...'
        
        return summary
    
    def _calculate_sentence_importance(self, sentence: str, doc, position: int, total_sentences: int) -> float:
        """Calculate importance score for a sentence"""
        score = 0.0
        sent_lower = sentence.lower()
        
        # Find sentence span
        for sent in doc.sents:
            if sent.text.strip() == sentence.strip():
                # Entities boost
                entities_in_sent = [e for e in doc.ents if e.sent == sent]
                score += len(entities_in_sent) * 2.0
                
                # Position boost (beginning/end)
                if position < 3 or position > total_sentences - 3:
                    score += 1.0
                
                # Length boost (ideal range)
                if 20 < len(sentence) < 200:
                    score += 1.0
                
                break
        
        # Keyword boost
        important_keywords = ['prazo', 'valor', 'contrato', 'responsabilidade', 'obrigação', 
                            'direito', 'data', 'vencimento', 'pagamento', 'multa', 'rescisão']
        for keyword in important_keywords:
            if keyword in sent_lower:
                score += 0.5
        
        # Number boost
        if re.search(r'\d+', sentence):
            score += 1.0
        
        return score

    def _identify_missing_topics(self, doc, text: str) -> List[str]:
        """Legacy method - kept for backward compatibility"""
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
    
    def _identify_missing_topics_improved(self, doc, text: str) -> List[str]:
        """Improved missing topics identification with document type detection and semantic analysis"""
        # Detect document type
        doc_type = self._detect_document_type(text)
        
        # Define topics by document type
        topics_by_type = {
            'contract': [
                'prazo', 'prazo de', 'prazo para', 'prazo de entrega',
                'valor', 'preço', 'valor total', 'pagamento', 'forma de pagamento',
                'responsabilidade', 'obrigações', 'direitos',
                'rescisão', 'cancelamento', 'término',
                'multa', 'penalidade', 'indenização',
                'foro', 'jurisdição', 'lei aplicável',
                'vigência', 'validade'
            ],
            'term': [
                'aceitação', 'aceitar', 'concordância',
                'cancelamento', 'rescisão',
                'privacidade', 'confidencialidade', 'sigilo',
                'dados pessoais', 'proteção de dados',
                'direitos do usuário', 'obrigações do usuário'
            ],
            'agreement': [
                'prazo', 'prazo de',
                'valor', 'pagamento',
                'responsabilidade', 'obrigações', 'direitos',
                'rescisão', 'cancelamento',
                'confidencialidade'
            ],
            'generic': [
                'prazo', 'prazo de',
                'valor', 'pagamento',
                'responsabilidade', 'obrigações', 'direitos',
                'rescisão', 'cancelamento',
                'confidencialidade', 'sigilo',
                'multa', 'penalidade',
                'foro', 'jurisdição'
            ]
        }
        
        topics_to_check = topics_by_type.get(doc_type, topics_by_type['generic'])
        text_lower = text.lower()
        missing = []
        
        for topic in topics_to_check:
            # Check if topic is present using multiple methods
            if not self._topic_present(topic, doc, text_lower):
                # Format topic name nicely
                topic_formatted = topic.replace('_', ' ').title()
                if topic_formatted not in missing:
                    missing.append(topic_formatted)
        
        return missing[:10]
    
    def _topic_present(self, topic: str, doc, text_lower: str) -> bool:
        """Check if a topic is present in the document using semantic similarity"""
        # Direct string match
        if topic.lower() in text_lower:
            return True
        
        # Check for variations
        topic_words = topic.lower().split()
        if len(topic_words) > 1:
            # Check if all words are present (even if not together)
            if all(word in text_lower for word in topic_words if len(word) > 2):
                return True
        
        # Check for semantic similarity using spaCy (if model supports it)
        try:
            nlp_model = self.nlp
            if nlp_model and hasattr(nlp_model.vocab, 'vectors') and len(nlp_model.vocab.vectors) > 0:
                topic_doc = nlp_model(topic)
                # Check similarity with key sentences
                max_similarity = 0.0
                for sent in list(doc.sents)[:20]:  # Check first 20 sentences
                    if topic_doc.vector_norm and sent.vector_norm:
                        similarity = topic_doc.similarity(sent)
                        max_similarity = max(max_similarity, similarity)
                
                # If similarity is high enough, topic is considered present
                if max_similarity > 0.5:
                    return True
        except Exception as e:
            logger.debug(f'Error checking semantic similarity for topic {topic}: {str(e)}')
        
        return False
    
    def _detect_document_type(self, text: str) -> str:
        """Detect the type of document based on content"""
        text_lower = text.lower()
        
        # Contract indicators
        contract_keywords = ['contrato', 'contratante', 'contratado', 'cláusula', 
                           'obrigações das partes', 'prazo de vigência']
        if any(keyword in text_lower for keyword in contract_keywords):
            return 'contract'
        
        # Term indicators
        term_keywords = ['termo', 'termos de uso', 'aceitar os termos', 'concordar com os termos',
                        'política de privacidade', 'dados pessoais']
        if any(keyword in text_lower for keyword in term_keywords):
            return 'term'
        
        # Agreement indicators
        agreement_keywords = ['acordo', 'convênio', 'parceria', 'colaboração']
        if any(keyword in text_lower for keyword in agreement_keywords):
            return 'agreement'
        
        return 'generic'

    def _extract_key_points(self, sentences: List[str], key_nouns: List[str]) -> List[str]:
        """Legacy method - kept for backward compatibility"""
        key_points = []
        
        for sentence in sentences[:20]:
            sentence_lower = sentence.lower()
            for noun in key_nouns[:5]:
                if noun in sentence_lower and len(sentence) > 20:
                    key_points.append(sentence[:200])
                    break
        
        return key_points[:10]
    
    def _extract_key_points_improved(self, sentences: List[str], key_nouns: List[str], doc) -> List[str]:
        """Improved key points extraction using information density"""
        key_points = []
        seen_sentences = set()
        
        # Score sentences by information density
        for i, sentence in enumerate(sentences[:30]):  # Check more sentences
            if sentence in seen_sentences:
                continue
            
            score = 0
            sentence_lower = sentence.lower()
            
            # Check for key nouns
            for noun in key_nouns[:8]:  # Check more nouns
                if noun in sentence_lower:
                    score += 2
            
            # Check for entities in sentence
            for sent in doc.sents:
                if sent.text.strip() == sentence.strip():
                    entities_in_sent = [e for e in doc.ents if e.sent == sent]
                    score += len(entities_in_sent) * 1.5
                    break
            
            # Check for important keywords
            important_keywords = ['prazo', 'valor', 'responsabilidade', 'obrigação', 
                               'direito', 'multa', 'rescisão', 'vencimento', 'pagamento']
            for keyword in important_keywords:
                if keyword in sentence_lower:
                    score += 1
            
            # Prefer sentences with numbers
            if re.search(r'\d+', sentence):
                score += 1
            
            # Prefer medium-length sentences
            if 30 < len(sentence) < 250:
                score += 1
            
            if score >= 2 and len(sentence) > 20:  # Minimum threshold
                key_points.append((sentence[:200], score))
                seen_sentences.add(sentence)
        
        # Sort by score and return top sentences
        key_points.sort(key=lambda x: x[1], reverse=True)
        return [kp[0] for kp in key_points[:10]]

    def _generate_recommendations(self, doc, text: str) -> List[str]:
        """Legacy method - kept for backward compatibility"""
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
    
    def _generate_recommendations_improved(self, doc, text: str) -> List[str]:
        """Improved recommendations based on contextual completeness analysis"""
        recommendations = []
        text_lower = text.lower()
        
        # Check for signatory information
        signatory_terms = ['assinatura', 'signatário', 'assinante', 'parte signatária']
        if not any(term in text_lower for term in signatory_terms):
            recommendations.append('Considerar adicionar informações sobre signatários e suas responsabilidades')
        
        # Check for dates
        date_terms = ['data', 'dia', 'prazo', 'vencimento', 'vigência', 'validade']
        if not any(term in text_lower for term in date_terms):
            recommendations.append('Adicionar datas importantes ao documento (início, término, prazos)')
        
        # Check for monetary values
        monetary_terms = ['valor', 'preço', 'pagamento', 'r$', 'reais', 'custo']
        if not any(term in text_lower for term in monetary_terms):
            recommendations.append('Considerar especificar valores monetários quando aplicável')
        
        # Check for responsibilities/obligations
        obligation_terms = ['responsabilidade', 'obrigação', 'dever', 'compromisso']
        if not any(term in text_lower for term in obligation_terms):
            recommendations.append('Especificar claramente as responsabilidades e obrigações de cada parte')
        
        # Check for termination clauses
        termination_terms = ['rescisão', 'cancelamento', 'término', 'encerramento']
        if not any(term in text_lower for term in termination_terms):
            recommendations.append('Incluir cláusulas sobre condições de rescisão ou cancelamento')
        
        # Check document length
        if len(text) < 500:
            recommendations.append('Documento pode ser expandido com mais detalhes e especificações')
        elif len(text) < 1000:
            recommendations.append('Considerar adicionar mais detalhes sobre termos e condições')
        
        # Check for jurisdiction/legal framework
        legal_terms = ['foro', 'jurisdição', 'lei aplicável', 'legislação', 'código']
        if not any(term in text_lower for term in legal_terms):
            recommendations.append('Especificar foro e jurisdição aplicável ao documento')
        
        # Check for confidentiality
        confidentiality_terms = ['confidencialidade', 'sigilo', 'privacidade', 'dados confidenciais']
        if not any(term in text_lower for term in confidentiality_terms) and len(text) > 1000:
            recommendations.append('Considerar adicionar cláusula de confidencialidade se aplicável')
        
        return recommendations[:5]

    def _identify_risks(self, doc, text: str) -> List[str]:
        """Legacy method - kept for backward compatibility"""
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
    
    def _identify_risks_improved(self, doc, text: str) -> List[str]:
        """Improved risk identification using linguistic patterns"""
        risks = []
        text_lower = text.lower()
        
        # Check for penalty clauses
        penalty_patterns = ['multa', 'penalidade', 'sanção', 'indenização']
        if any(pattern in text_lower for pattern in penalty_patterns):
            risks.append('Verificar cláusulas de multa e penalidades - avaliar valores e condições')
        
        # Check for termination clauses
        termination_patterns = ['rescisão', 'cancelamento', 'término', 'encerramento']
        if any(pattern in text_lower for pattern in termination_patterns):
            risks.append('Revisar termos de rescisão - verificar condições e prazos')
        
        # Check for absolute terms (high risk)
        absolute_terms = ['sempre', 'nunca', 'obrigatoriamente', 'proibido', 'vedado']
        if any(term in text_lower for term in absolute_terms):
            risks.append('Documento contém termos absolutos - revisar se são apropriados')
        
        # Check for conditional clauses
        conditional_patterns = ['se não', 'caso não', 'na hipótese de', 'em caso de']
        conditional_count = sum(1 for pattern in conditional_patterns if pattern in text_lower)
        if conditional_count >= 2:
            risks.append('Múltiplas cláusulas condicionais identificadas - verificar todas as condições')
        
        # Check for confidentiality
        if 'confidencialidade' in text_lower or 'sigilo' in text_lower:
            risks.append('Confirmar cláusulas de confidencialidade e suas exceções')
        
        # Check for indemnification
        indemnification_patterns = ['indenização', 'indenizar', 'responsabilidade civil']
        if any(pattern in text_lower for pattern in indemnification_patterns):
            risks.append('Avaliar cláusulas de indenização e limites de responsabilidade')
        
        # Check for jurisdiction
        if 'jurisdição' in text_lower or 'foro' in text_lower:
            risks.append('Verificar foro e jurisdição aplicável - confirmar se está correto')
        
        # Check for ambiguous terms
        ambiguous_terms = ['razoável', 'adequado', 'necessário', 'quando apropriado']
        ambiguous_count = sum(1 for term in ambiguous_terms if term in text_lower)
        if ambiguous_count >= 3:
            risks.append('Documento contém vários termos subjetivos - considerar especificar critérios objetivos')
        
        # Check document completeness
        if len(text) < 500:
            risks.append('Documento muito curto - pode estar incompleto ou faltando informações importantes')
        
        # Default risk if no specific risks found
        if not risks:
            risks.append('Documento parece estar em formato básico - considerar revisão jurídica completa')
        
        return risks[:5]
    
    def _extract_obligations_and_rights(self, doc) -> List[str]:
        """Extract obligations and rights from the document"""
        obligations = []
        rights = []
        
        # Keywords for obligations
        obligation_keywords = ['deve', 'deverá', 'obrigado', 'obrigação', 'compromete-se', 
                            'responsável por', 'deve garantir']
        # Keywords for rights
        right_keywords = ['tem direito', 'pode', 'poderá', 'autorizado', 'permitido', 
                         'facultado', 'pode solicitar']
        
        for sent in doc.sents:
            sent_lower = sent.text.lower()
            
            # Check for obligations
            for keyword in obligation_keywords:
                if keyword in sent_lower and len(sent.text) > 30:
                    obligations.append(sent.text[:200])
                    break
            
            # Check for rights
            for keyword in right_keywords:
                if keyword in sent_lower and len(sent.text) > 30:
                    rights.append(sent.text[:200])
                    break
        
        result = []
        if obligations:
            result.append(f'Obrigações identificadas: {len(obligations)}')
        if rights:
            result.append(f'Direitos identificados: {len(rights)}')
        
        return result[:3]
    
    def _identify_risk_patterns(self, doc, text: str) -> List[str]:
        """Identify linguistic risk patterns in the document"""
        risk_patterns = []
        text_lower = text.lower()
        
        # Pattern: Unclear conditions
        if re.search(r'se\s+\w+\s+então', text_lower):
            risk_patterns.append('Cláusulas condicionais identificadas - verificar todas as condições')
        
        # Pattern: High penalty values
        if re.search(r'multa\s+de\s+[r$]?\s*\d+', text_lower, re.IGNORECASE):
            risk_patterns.append('Valores de multa identificados - verificar se são proporcionais')
        
        # Pattern: Unilateral obligations
        obligation_verbs = ['deve', 'deverá', 'obrigado']
        if sum(1 for verb in obligation_verbs if verb in text_lower) > 5:
            risk_patterns.append('Múltiplas obrigações identificadas - verificar se são equilibradas')
        
        return risk_patterns


