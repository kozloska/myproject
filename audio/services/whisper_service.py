# audio/services/whisper_service.py
from faster_whisper import WhisperModel
import logging
import os

logger = logging.getLogger(__name__)

class WhisperTranscriber:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            model_path = "/home/user/Downloads/faster-whisper-large-v3"
            logger.info("Загрузка Faster-Whisper large-v3...")
            cls._model = WhisperModel(
                model_path,
                device="cpu",
                compute_type="int8"
            )
            logger.info("Faster-Whisper large-v3 загружена.")
        return cls._model

    @classmethod
    def transcribe(cls, file_path: str, language: str = "ru") -> str:
        model = cls.get_model()
        segments, _ = model.transcribe(file_path, language=language, beam_size=5)
        return "".join(segment.text for segment in segments).strip()