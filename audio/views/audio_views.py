from django.core.files.storage import default_storage
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import os
from ..models import AudioFile, Project
from ..serializers import AudioUploadSerializer
from ..services.audio_service import AudioService
from ..services.transcription_service import TranscriptionService
import logging
from audio.services.task import process_audio_task

logger = logging.getLogger(__name__)


@api_view(['POST'])
def upload_audio(request):
    logger.info("Audio upload request received")

    serializer = AudioUploadSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        audio_file = serializer.save()  # Теперь project_id доступен в serializer.context
        project_id = serializer.context['project_id']

        # Валидация файла
        AudioService.validate_audio_file(audio_file.audio.name)

        # Запускаем асинхронную задачу
        task = process_audio_task.delay(audio_file.id, project_id)

        return Response({
            "message": "Audio processing started",
            "task_id": task.id
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"Error in upload_audio: {str(e)}")
        if 'audio_file' in locals():
            audio_file.delete()
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )