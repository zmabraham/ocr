"""Hebrew Text Analysis using DictaBERT"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM

from ..config import settings


@dataclass
class TextError:
    """Represents a potential OCR error"""
    word: str
    position: int
    confidence: float
    context: str
    suggestions: List[str]
    bbox: Optional[List[int]] = None


@dataclass
class AnalysisResult:
    """Result of text analysis"""
    errors: List[TextError]
    total_words: int
    hebrew_percentage: float
    overall_quality: float


class DictaBERTAnalyzer:
    """Analyze Hebrew text using DictaBERT models"""

    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")

        # Load base DictaBERT model
        self.model_name = settings.DICTABERT_MODEL
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForMaskedLM.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

    def analyze_text(self, ocr_text: str, ocr_words: List[Dict]) -> AnalysisResult:
        """
        Analyze OCR text for potential errors

        Args:
            ocr_text: Full OCR text
            ocr_words: List of word objects with confidence scores

        Returns:
            AnalysisResult with detected errors
        """
        errors = []
        total_words = len(ocr_words)

        # Find low confidence words
        low_confidence = [
            w for w in ocr_words
            if w['confidence'] < settings.CONFIDENCE_LOW
        ]

        # Analyze each low-confidence word
        for word_info in low_confidence:
            word = word_info['text']
            if not word.strip():
                continue

            # Get context (surrounding words)
            context = self._get_context(ocr_text, word_info['position'])

            # Generate suggestions
            suggestions = self._generate_suggestions(word, context)

            errors.append(TextError(
                word=word,
                position=word_info['position'],
                confidence=word_info['confidence'],
                context=context,
                suggestions=suggestions,
                bbox=word_info.get('bbox')
            ))

        # Calculate quality metrics
        hebrew_ratio = self._calculate_hebrew_percentage(ocr_text)
        overall_quality = self._calculate_quality(ocr_words)

        return AnalysisResult(
            errors=errors,
            total_words=total_words,
            hebrew_percentage=hebrew_ratio,
            overall_quality=overall_quality
        )

    def _get_context(self, text: str, position: int, window: int = 5) -> str:
        """Get surrounding words for context"""
        words = text.split()
        start = max(0, position - window)
        end = min(len(words), position + window + 1)
        return ' '.join(words[start:end])

    def _generate_suggestions(self, word: str, context: str,
                           num_suggestions: int = 5) -> List[str]:
        """
        Generate correction suggestions for a word using DictaBERT

        Args:
            word: The word to correct
            context: Surrounding text context
            num_suggestions: Number of suggestions to return

        Returns:
            Ranked list of suggestions
        """
        if not word or len(word) < 2:
            return []

        # Create masked input
        masked_context = context.replace(word, '[MASK]')

        try:
            inputs = self.tokenizer(masked_context, return_tensors='pt')
            inputs = inputs.to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = outputs.logits

            # Find the mask token position
            mask_idx = (inputs['input_ids'][0] == self.tokenizer.mask_token_id).nonzero(as_tuple=True)[0]

            if len(mask_idx) == 0:
                return [word]

            # Get top predictions for the masked token
            mask_token_logits = predictions[0, mask_idx, :]
            top_indices = torch.topk(mask_token_logits, num_suggestions + 1)[1]

            suggestions = []
            for idx in top_indices[1:]:  # Skip the original word if present
                suggestion = self.tokenizer.decode([idx])
                if suggestion and suggestion != word:
                    suggestions.append(suggestion)

            # Add the original word as fallback
            if len(suggestions) < num_suggestions:
                suggestions.append(word)

            return suggestions[:num_suggestions]

        except Exception as e:
            print(f"Error generating suggestions for '{word}': {e}")
            return [word]

    def _calculate_hebrew_percentage(self, text: str) -> float:
        """Calculate percentage of Hebrew characters"""
        hebrew_chars = set('אבגדהוזחטיכלמנסעפצקרשת')
        total_chars = len([c for c in text if c.isalpha()])
        hebrew_chars_count = sum(1 for c in text if c in hebrew_chars)

        if total_chars == 0:
            return 0.0

        return (hebrew_chars_count / total_chars) * 100

    def _calculate_quality(self, ocr_words: List[Dict]) -> float:
        """Calculate overall OCR quality score"""
        if not ocr_words:
            return 0.0

        confidences = [w['confidence'] for w in ocr_words]
        return sum(confidences) / len(confidences)


class CorrectionSuggester:
    """Generate and rank correction suggestions"""

    def __init__(self):
        # Common Hebrew OCR corrections mapping
        self.common_corrections = {
            'ת': 'ת',  # Fix common OCR confusions
            'מ': 'ם',  # Mem confusion
            'נ': 'ן',  # Nun confusion
            # Add more common substitutions based on visual similarity
        }

        # Vowel point (nikud) corrections
        self.nikud_corrections = {
            # Common nikud OCR errors
        }

    def suggest_corrections(self, word: str, context: str,
                           dicta_suggestions: List[str]) -> List[Dict]:
        """
        Generate ranked correction suggestions

        Returns:
            List of suggestions with confidence scores
        """
        suggestions = []

        # Add DictaBERT suggestions
        for i, suggestion in enumerate(dicta_suggestions):
            score = 1.0 - (i * 0.15)  # Decreasing score for lower ranks
            suggestions.append({
                'text': suggestion,
                'score': score,
                'source': 'dictabert'
            })

        # Add common corrections if not already present
        for correction, original in self.common_corrections.items():
            if correction not in [s['text'] for s in suggestions]:
                if self._visual_similarity(word, original) > 0.7:
                    suggestions.append({
                        'text': correction,
                        'score': 0.6,
                        'source': 'common'
                    })

        # Sort by score and return top 5
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:5]

    def _visual_similarity(self, word1: str, word2: str) -> float:
        """Calculate visual similarity between two words"""
        if word1 == word2:
            return 1.0

        # Simple Levenshtein-based similarity
        from difflib import SequenceMatcher

        return SequenceMatcher(None, word1, word2).ratio()
