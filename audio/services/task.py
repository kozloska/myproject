from celery import shared_task
from django.core.files.storage import default_storage
import os

from .transcription_service import TranscriptionService
from ..services.audio_service import AudioService
from ..models import AudioFile


@shared_task(bind=True)
def process_audio_task(self, audio_file_id, project_id):
    try:
        audio_file = AudioFile.objects.get(id=audio_file_id)
        audio_file_path = default_storage.path(audio_file.audio.name)

        # Конвертация и транскрибация
        if not audio_file.audio.name.endswith('.wav'):
            converted_path = audio_file_path.replace(os.path.splitext(audio_file.audio.name)[1], '.wav')
            AudioService.convert_to_wav(audio_file_path, converted_path)
            audio_file_path = converted_path

        transcribed_text = AudioService.transcribe_audio(audio_file_path)
        questions = TranscriptionService.extract_questions(transcribed_text)
        TranscriptionService.save_questions(questions, project_id)

        # Удаление временных файлов
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)
        if hasattr(audio_file, 'converted_path') and os.path.exists(audio_file.converted_path):
            os.remove(audio_file.converted_path)

        audio_file.delete()

        return {"status": "success", "transcribed_text": transcribed_text}
    except Exception as e:
        # Очистка в случае ошибки
        if 'audio_file' in locals() and audio_file.id:
            audio_file.delete()
        if 'audio_file_path' in locals() and os.path.exists(audio_file_path):
            os.remove(audio_file_path)
        raise self.retry(exc=e, countdown=60)