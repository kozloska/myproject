# audio/task.py
import os
import time
import logging
import tempfile
from celery import shared_task
from django.core.files.storage import default_storage

from .services.LLMProcessor_service import LLMProcessor
from .services.whisper_service import WhisperTranscriber
from .services.transcript_cleaner import clean_transcription
from .models import AudioFile, Project, Question

# Настройка логгера
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def process_audio_in_memory_task(self, audio_bytes, file_name, project_id):
    temp_path = None
    task_start = time.time()
    task_id = self.request.id
    
    try:
        # 1. Обновляем статус проекта
        project = Project.objects.get(ID=project_id)
        project.Status = "Вопросы расшифровываются"
        project.save(update_fields=['Status'])
        # 2. Сохраняем временный файл
        ext = os.path.splitext(file_name)[1].lower() or '.mp3'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name
        
        # 3. Транскрибация (Whisper)
        transcription = WhisperTranscriber.transcribe(temp_path, language="ru")
       
        # 4. Очистка транскрипта
        clean_start = time.time()
        cleaned_transcription = clean_transcription(transcription)
               
        # Удаляем временный файл
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
            temp_path = None
      

        # 5. Генерация вопросов (LLM)
        llm = LLMProcessor(model_path="/opt/deepseek-r1-distill-qwen-14b-q4_k_m.gguf")
        llm_questions = llm.generate_questions(cleaned_transcription)
        
        # 6. Сохранение вопросов в БД
        created_count = 0
        for q_text in llm_questions:
            Question.objects.create(
                Text=q_text.strip(),
                ID_Project=project,
                Status=False
            )
            created_count += 1
        
        # 7. Финальный статус
        total_time = time.time() - task_start
        project.Status = "Готов"
        project.save(update_fields=['Status'])
        
        return f"Success: {created_count} questions generated in {total_time:.2f}s"

    except Exception as exc:
        
        # Очистка временного файла
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"[Task {task_id}] Could not delete temp file: {e}")
        
        # Обновление статуса проекта
        project = Project.objects.get(ID=project_id)
        project.Status = f"Ошибка: {type(exc).__name__}"
        project.save(update_fields=['Status'])
       # Повтор задачи
        raise self.retry(exc=exc, countdown=60)
    
    finally:
        # Страховка: удалить файл, если он остался
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass