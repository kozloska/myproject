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
        serializer = AudioUploadSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        audio_file = serializer.save()
        project_id = serializer.context['project_id']

        project = Project.objects.get(ID=project_id)
        project.Status = "Вопросы расшифровываются"
        project.save()

        # Запускаем асинхронную задачу
        process_audio_task.apply_async(args=[audio_file.id, project_id])

        return Response(
            {"message": "Audio processing started", "task_id": process_audio_task.request.id},
            status=status.HTTP_202_ACCEPTED
        )

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )