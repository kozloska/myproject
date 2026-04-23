# audio/tasks.py
#celery -A myproject worker --loglevel=info
from audio.services.LLMProcessor_service import LLMProcessor
from celery import shared_task
import tempfile
import os
import logging
from django.core.files.storage import default_storage

from .services.whisper_service import WhisperTranscriber
from .models import AudioFile, Project, Question

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2)
def process_audio_in_memory_task(self, audio_bytes, file_name, project_id):
    temp_path = None
    try:
        project = Project.objects.get(ID=project_id)
        project.Status = "Вопросы расшифровываются"
        project.save()

        #Сохраняем временный файл
        ext = os.path.splitext(file_name)[1].lower() or '.mp3'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        #Транскрибация
        transcription = WhisperTranscriber.transcribe(temp_path, language="ru")
        print(f"\nТРАНСКРИПТ:\n{transcription}\n")
        #Удаляем временный файл 
        os.unlink(temp_path)
        temp_path = None

        #Генерация вопросов через LLM
        llm = LLMProcessor(model_path="/opt/deepseek-r1-distill-qwen-14b-q4_k_m.gguf")
        llm_questions = llm.generate_questions(transcription)
        print(f"Вопросы от LLM:")
        for i, q in enumerate(llm_questions, 1):
            print(f"  {i}. {q}")

        # Сохранение
        for q in llm_questions:
            Question.objects.create(Text=q.strip(), ID_Project=project, Status=False)

        project.Status = "Готов"
        project.save()

    except Exception as exc:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        project = Project.objects.get(ID=project_id)
        project.Status = "Ошибка загрузки аудио"
        project.save()
        raise self.retry(exc=exc, countdown=60)