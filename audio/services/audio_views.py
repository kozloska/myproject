# views.py
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from audio.models import Project
from audio.task import process_audio_task
import logging

from audio.serializers import AudioUploadSerializer

logger = logging.getLogger(__name__)
@csrf_exempt
@api_view(['POST'])
def upload_audio(request):
    try:
        logger.debug(f"Received data: {request.data}")
        serializer = AudioUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Сохраняем файл и получаем file_path и project_id
        result = serializer.save()
        file_path = result['file_path']
        project_id = result['project_id']

        # Проверяем существование проекта
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            logger.error(f"Project with id {project_id} not found")
            return Response(
                {"error": f"Project with id {project_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        project.Status = "Вопросы расшифровываются"
        project.save()

        # Запускаем асинхронную задачу
        task = process_audio_task.apply_async(args=[file_path, project_id])

        return Response(
            {"message": "Audio processing started", "task_id": task.id},
            status=status.HTTP_202_ACCEPTED
        )

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )