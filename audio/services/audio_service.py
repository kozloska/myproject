import os
from pydub import AudioSegment
from django.core.files.storage import default_storage
import whisper
import logging

logger = logging.getLogger(__name__)


class AudioService:
    ALLOWED_EXTENSIONS = ['.wav', '.mp3', '.ogg', '.flac', '.3gp', '.m4a']

    @classmethod
    def validate_audio_file(cls, file_name):
        if not any(file_name.endswith(ext) for ext in cls.ALLOWED_EXTENSIONS):
            raise ValueError("Unsupported file format")

    @classmethod
    def convert_to_wav(cls, input_path, output_path):
        try:
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format='wav')
            return output_path
        except Exception as e:
            logger.error(f"Audio conversion error: {str(e)}")
            raise

    @classmethod
    def transcribe_audio(cls, file_path, language='ru'):
        try:
            model = whisper.load_model("small")
            result = model.transcribe(file_path, language=language)
            return result['text']
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            raise