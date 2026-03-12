import tempfile
from threading import Lock

from paddleocr import PaddleOCR
from pdf2image import convert_from_bytes


class OCREngine:
    def __init__(self) -> None:
        self._ocr = PaddleOCR(lang="ar", use_angle_cls=True, show_log=False)

    def extract_text(self, file_bytes: bytes, suffix: str) -> str:
        if suffix == ".pdf":
            return self._extract_from_pdf(file_bytes)
        return self._extract_from_image_bytes(file_bytes, suffix=suffix)

    def _extract_from_pdf(self, pdf_bytes: bytes) -> str:
        pages = convert_from_bytes(pdf_bytes)
        page_texts = []
        for page in pages:
            with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
                page.save(tmp.name, "PNG")
                result = self._ocr.ocr(tmp.name, cls=True)
                page_texts.append(self._flatten_result(result))
        return "\n".join(page_texts)

    def _extract_from_image_bytes(self, image_bytes: bytes, suffix: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(image_bytes)
            tmp.flush()
            result = self._ocr.ocr(tmp.name, cls=True)
        return self._flatten_result(result)

    @staticmethod
    def _flatten_result(result: list) -> str:
        texts = []
        for line in result or []:
            for block in line or []:
                if len(block) > 1 and block[1]:
                    texts.append(block[1][0])
        return "\n".join(texts)


class OCREngineSingleton:
    _instance: OCREngine | None = None
    _lock = Lock()

    @classmethod
    def get_engine(cls) -> OCREngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = OCREngine()
        return cls._instance
