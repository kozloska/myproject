import os
from django.core.files.storage import default_storage
from celery import shared_task

from audio.services.LLMProcessor_service import LLMProcessor
from audio.services.audio_service import AudioService
from audio.services.transcription_service import TranscriptionService
from audio.models import AudioFile, Project
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_audio_task(self, file_path, project_id):
    audio_file_path = file_path
    original_file_path = file_path
    llm_processor = None
    try:
        # Проверяем существование проекта
        project = Project.objects.get(id=project_id)

        # Конвертация в WAV, если нужно
        if not audio_file_path.endswith('.wav'):
            converted_path = f"{audio_file_path}.wav"
            AudioService.convert_to_wav(audio_file_path, converted_path)
            audio_file_path = converted_path

        # Транскрипция аудио
        transcribed_text = AudioService.transcribe_audio(audio_file_path)

        # Сохранение текста в Project
        project.Text = transcribed_text
        project.Status = "Транскрипция завершена"
        project.save()

        # Генерация вопросов через LLM
        llm_processor = LLMProcessor.get_instance()
        questions = llm_processor.generate_questions(transcribed_text)

        # Сохранение вопросов в таблицу Question
        TranscriptionService.save_questions(questions, project_id)

        return {
            "status": "success",
            "transcribed_text": transcribed_text,
            "questions": questions
        }

    except Exception as exc:
        logger.error(f"Audio processing failed: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)

    finally:
        # Удаляем файлы (исходный и конвертированный, если был создан)
        for file_path in [audio_file_path, original_file_path]:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete file {file_path}: {str(e)}")
        # Освобождаем ресурсы модели
        if llm_processor:
            llm_processor.close()