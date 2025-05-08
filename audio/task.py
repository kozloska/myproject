import os
from django.core.files.storage import default_storage
from celery import shared_task
from audio.services.audio_service import AudioService
from audio.services.transcription_service import TranscriptionService
from audio.models import AudioFile
import logging


logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_audio_task(self, audio_file_id, project_id):
    audio_file = None
    audio_file_path = None
    try:
        audio_file = AudioFile.objects.get(id=audio_file_id)
        audio_file_path = default_storage.path(audio_file.audio.name)

        if not audio_file.audio.name.endswith('.wav'):
            converted_path = f"{audio_file_path}.wav"
            AudioService.convert_to_wav(audio_file_path, converted_path)
            audio_file_path = converted_path

        transcribed_text = AudioService.transcribe_audio(audio_file_path)
        questions = TranscriptionService.extract_questions(transcribed_text)
        TranscriptionService.save_questions(questions, project_id)

        return {"status": "success", "transcribed_text": transcribed_text}

    except Exception as exc:
        logger.error(f"Audio processing failed: {str(exc)}")
        if audio_file:
            audio_file.delete()
        raise self.retry(exc=exc, countdown=60)

    finally:
        if audio_file_path and os.path.exists(audio_file_path):
            os.remove(audio_file_path)
        if audio_file:
            audio_file.delete()