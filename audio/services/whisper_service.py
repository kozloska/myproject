# audio/services/whisper_service.py
import whisper
import logging
import os

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            try:
                cls._model = whisper.load_model("small")
            except Exception as e:
                cls._model = None
                raise e
        return cls._model

    @classmethod
    def transcribe(cls, file_path: str, language: str = "ru") -> str:
        model = cls.get_model()
        if model is None:
            raise RuntimeError("Модель Whisper не инициализирована")
        
        # ← openai-whisper возвращает dict, а не segments
        result = model.transcribe(file_path, language=language)
        return result["text"].strip()