# audio/views.py
import os
import logging
from django.core.files.storage import default_storage
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Specialization
from .serializers import AudioFileSerializer
import whisper
from pydub import AudioSegment

# Настройка логгера
logger = logging.getLogger(__name__)
@api_view(['POST'])
def upload_audio(request):
    if request.method == 'POST':
        serializer = AudioFileSerializer(data=request.data)
        if serializer.is_valid():
            audio_file = serializer.save()
            audio_file_path = default_storage.path(audio_file.audio.name)

            logger.info(f"Путь к аудиофайлу: {audio_file_path}")

            # Проверка формата файла
            allowed_extensions = ['.wav', '.mp3', '.ogg', '.flac', '.3gp']
            if not any(audio_file.audio.name.endswith(ext) for ext in allowed_extensions):
                logger.error("Неподдерживаемый формат файла")
                return Response({"error": "Неподдерживаемый формат файла"}, status=status.HTTP_400_BAD_REQUEST)

            # Проверяем, существует ли файл
            if not os.path.exists(audio_file_path):
                logger.error(f"Файл не найден по пути: {audio_file_path}")
                return Response({"error": "Файл не найден"}, status=status.HTTP_404_NOT_FOUND)

            # Конвертация файла в WAV, если это необходимо
            converted_file_path = audio_file_path.replace(os.path.splitext(audio_file.audio.name)[1], '.wav')
            if audio_file.audio.name.endswith('.wav'):
                converted_file_path = audio_file_path  # Если файл уже в WAV, не конвертируем
            else:
                try:
                    audio = AudioSegment.from_file(audio_file_path)
                    audio.export(converted_file_path, format='wav')
                    logger.info(f"Файл конвертирован в WAV: {converted_file_path}")
                except Exception as e:
                    logger.error(f"Ошибка при конвертации файла: {str(e)}")
                    return Response({"error": "Ошибка при конвертации файла"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                model = whisper.load_model("small")  # Измените на "medium", если необходимо
            except Exception as e:
                logger.error(f"Ошибка при загрузке модели: {str(e)}")
                return Response({"error": "Ошибка при загрузке модели"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                logger.info("Начинаю транскрибирование...")
                result = model.transcribe(converted_file_path, language='ru')  # Укажите язык
                return Response(result, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Ошибка при транскрибировании: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.error(f"Ошибка валидации: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def specialization_list(request):
    specializations = Specialization.objects.all().values('id', 'name')  # Получаем все записи
    specializations_list = list(specializations)  # Преобразуем QuerySet в список
    return JsonResponse(specializations_list, safe=False)  # Возвращаем JSON-ответ
