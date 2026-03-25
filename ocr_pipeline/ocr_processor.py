"""OCR Processing Engine for Hebrew/Yiddish/Aramaic Text"""
import os
import tempfile
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    import numpy as np
except ImportError as e:
    print(f"Missing dependency: {e}")
    raise

from ..config import settings


@dataclass
class OCRResult:
    """Result from OCR processing"""
    text: str
    confidence: float
    words: List[Dict[str, any]]
    pages: int
    image_paths: List[str]


class OCRProcessor:
    """Process PDFs and images with OCR optimized for Hebrew"""

    def __init__(self):
        self.tesseract_cmd = settings.TESSERACT_CMD
        self.lang = settings.TESSERACT_LANG

        # Configure Tesseract for Hebrew
        self.tesseract_config = r'--oem 1 --psm 6 -c tessedit_create_hocr 1'

    def process_pdf(self, file_path: str, dpi: int = 300) -> OCRResult:
        """
        Process a PDF file and return OCR results with confidence scores

        Args:
            file_path: Path to PDF file
            dpi: DPI for rendering (higher for low-res docs)

        Returns:
            OCRResult with text, confidence scores, and word-level data
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Convert PDF to images
        with tempfile.TemporaryDirectory() as temp_dir:
            image_paths = convert_from_path(
                str(file_path),
                dpi=dpi,
                output_folder=temp_dir,
                fmt='jpg',
                paths_only=True,
                grayscale=True
            )

            all_text = []
            all_words = []
            all_confidences = []

            # Process each page
            for img_path in image_paths:
                page_result = self._process_image(img_path)
                all_text.append(page_result['text'])
                all_words.extend(page_result['words'])
                all_confidences.extend(page_result['confidences'])

        # Calculate overall confidence
        overall_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        return OCRResult(
            text='\n\n'.join(all_text),
            confidence=overall_confidence,
            words=all_words,
            pages=len(image_paths),
            image_paths=image_paths
        )

    def _process_image(self, image_path: str) -> Dict[str, any]:
        """Process a single image with Tesseract"""
        # Get image data with confidence scores
        data = pytesseract.image_to_data(
            image_path,
            lang=self.lang,
            config=self.tesseract_config,
            output_type=pytesseract.Output.DICT
        )

        # Get plain text
        text = pytesseract.image_to_string(
            image_path,
            lang=self.lang,
            config=self.tesseract_config
        )

        # Extract words and confidences
        words = []
        confidences = []

        for item in data:
            if item.get('text') and item['text'].strip():
                conf = item.get('conf', 0)
                words.append({
                    'text': item['text'],
                    'bbox': item.get('bbox', []),
                    'confidence': conf,
                    'page_num': item.get('page_num', 0)
                })
                confidences.append(conf)

        return {
            'text': text,
            'words': words,
            'confidences': confidences
        }

    def preprocess_low_resolution(self, image_path: str, output_path: str) -> None:
        """
        Enhance low-resolution images before OCR

        Args:
            image_path: Input image path
            output_path: Enhanced output path
        """
        img = Image.open(image_path)

        # Convert to grayscale if needed
        if img.mode != 'L':
            img = img.convert('L')

        # Enhance contrast
        img = self._enhance_contrast(img)

        # Denoise
        img_array = np.array(img)
        img_denoised = self._denoise(img_array)

        # Save enhanced image
        Image.fromarray(img_denoised).save(output_path)

    def _enhance_contrast(self, image: Image.Image) -> Image.Image:
        """Enhance image contrast for better OCR"""
        from PIL import ImageEnhance

        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(2.0)

    def _denoise(self, img_array: np.ndarray) -> np.ndarray:
        """Apply denoising to image array"""
        import cv2

        # Use OpenCV for denoising
        denoised = cv2.fastNlMeansDenoising(img_array, None, h=10)
        return denoised

    def get_low_confidence_words(self, ocr_result: OCRResult,
                                threshold: float = None) -> List[Dict]:
        """
        Get words below confidence threshold for review

        Args:
            ocr_result: OCR processing result
            threshold: Confidence threshold (default from settings)

        Returns:
            List of words needing review
        """
        if threshold is None:
            threshold = settings.CONFIDENCE_LOW

        return [
            word for word in ocr_result.words
            if word['confidence'] < threshold
        ]


class ImageAnalyzer:
    """Analyze images to extract text regions and bounding boxes"""

    @staticmethod
    def extract_text_regions(image_path: str) -> List[Dict]:
        """
        Extract text regions with bounding boxes for visual verification

        Args:
            image_path: Path to image file

        Returns:
            List of text regions with bounding box coordinates
        """
        import cv2

        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Get text data with bounding boxes
        data = pytesseract.image_to_data(
            image_path,
            lang=settings.TESSERACT_LANG,
            output_type=pytesseract.Output.DICT
        )

        regions = []
        for item in data:
            if item.get('text') and item['text'].strip():
                bbox = item.get('bbox', [])
                if bbox:
                    regions.append({
                        'text': item['text'],
                        'bbox': bbox,
                        'confidence': item.get('conf', 0)
                    })

        return regions

    @staticmethod
    def crop_region(image_path: str, bbox: List[int], output_path: str) -> None:
        """Crop a specific region from an image for display"""
        img = Image.open(image_path)
        cropped = img.crop(bbox)
        cropped.save(output_path)
