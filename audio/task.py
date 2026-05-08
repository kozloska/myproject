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
    """
    Асинхронная задача обработки аудио:
    1. Сохранение временного файла
    2. Транскрибация через Whisper
    3. Очистка транскрипта
    4. Генерация вопросов через LLM
    5. Сохранение результатов в БД
    """
    temp_path = None
    task_start = time.time()
    task_id = self.request.id
    
    try:
        logger.info(f"🚀 [Task {task_id}] START | Project: {project_id}, File: {file_name}")

        # 1. Обновляем статус проекта
        project = Project.objects.get(ID=project_id)
        project.Status = "Вопросы расшифровываются"
        project.save(update_fields=['Status'])
        logger.info(f"✅ [Task {task_id}] Project status updated")

        # 2. Сохраняем временный файл
        ext = os.path.splitext(file_name)[1].lower() or '.mp3'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name
        
        file_size = os.path.getsize(temp_path)
        logger.info(f"💾 [Task {task_id}] Temp file saved: {temp_path} ({file_size / 1024:.1f} KB)")

        # 3. Транскрибация (Whisper)
        whisper_start = time.time()
        logger.info(f"🎤 [Task {task_id}] Starting Whisper transcription...")
        
        transcription = WhisperTranscriber.transcribe(temp_path, language="ru")
        whisper_time = time.time() - whisper_start
        
        logger.info(f"✅ [Task {task_id}] Whisper done in {whisper_time:.2f}s | Length: {len(transcription)} chars")
        logger.debug(f"📝 Raw transcript preview: {transcription[:200]}...")

        # 4. Очистка транскрипта
        clean_start = time.time()
        cleaned_transcription = clean_transcription(transcription)
        clean_time = time.time() - clean_start
        
        logger.info(f"🧹 [Task {task_id}] Transcription cleaned in {clean_time:.2f}s | {len(transcription)} → {len(cleaned_transcription)} chars")
        logger.debug(f"📝 Cleaned preview: {cleaned_transcription[:200]}...")

        # Удаляем временный файл
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
            temp_path = None
            logger.info(f"🗑️ [Task {task_id}] Temp file deleted")

        # 5. Генерация вопросов (LLM)
        llm_start = time.time()
        logger.info(f"🧠 [Task {task_id}] Initializing LLM and generating questions...")
        
        llm = LLMProcessor(model_path="/opt/deepseek-r1-distill-qwen-14b-q4_k_m.gguf")
        llm_questions = llm.generate_questions(cleaned_transcription)
        
        llm_time = time.time() - llm_start
        logger.info(f"✅ [Task {task_id}] LLM generated {len(llm_questions)} questions in {llm_time:.2f}s")
        
        for i, q in enumerate(llm_questions, 1):
            logger.info(f"   📋 Q{i}: {q.strip()[:80]}...")

        # 6. Сохранение вопросов в БД
        db_start = time.time()
        created_count = 0
        for q_text in llm_questions:
            Question.objects.create(
                Text=q_text.strip(),
                ID_Project=project,
                Status=False
            )
            created_count += 1
        
        db_time = time.time() - db_start
        logger.info(f"💾 [Task {task_id}] Saved {created_count} questions to DB in {db_time:.2f}s")

        # 7. Финальный статус
        total_time = time.time() - task_start
        project.Status = "Готов"
        project.save(update_fields=['Status'])
        
        logger.info(f"🏁 [Task {task_id}] COMPLETED | Total: {total_time:.2f}s | Questions: {created_count}")
        return f"Success: {created_count} questions generated in {total_time:.2f}s"

    except Exception as exc:
        # Логирование ошибки с полным стектрейсом
        logger.exception(f"❌ [Task {task_id}] FAILED: {type(exc).__name__}: {str(exc)}")
        
        # Очистка временного файла
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.info(f"🗑️ [Task {task_id}] Cleaned up temp file after error")
            except Exception as e:
                logger.warning(f"⚠️ [Task {task_id}] Could not delete temp file: {e}")
        
        # Обновление статуса проекта
        try:
            project = Project.objects.get(ID=project_id)
            project.Status = f"Ошибка: {type(exc).__name__}"
            project.save(update_fields=['Status'])
        except Exception as db_err:
            logger.error(f"⚠️ [Task {task_id}] Could not update project status: {db_err}")
            
        # Повтор задачи
        raise self.retry(exc=exc, countdown=60)
    
    finally:
        # Страховка: удалить файл, если он остался
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass