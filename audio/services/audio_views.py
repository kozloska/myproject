# views.py
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from audio.models import Project
from audio.task import process_audio_in_memory_task
import logging

from audio.serializers import AudioUploadSerializer

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
def upload_audio(request):
    project_id = request.data.get('project_id')
    audio_file = request.FILES.get('audio')

    if not project_id or not audio_file:
        return Response({"error": "project_id and audio required"}, status=400)

    try:
        project = Project.objects.get(ID=project_id)
        project.Status = "В обработке"
        project.save()

        # Передаём содержимое файла как bytes
        audio_bytes = audio_file.read()
        file_name = audio_file.name

        # Запускаем задачу с байтами
        process_audio_in_memory_task.delay(
            audio_bytes=audio_bytes,
            file_name=file_name,
            project_id=project_id
        )

        return Response({"message": "Обработка начата"}, status=202)

    except Exception as e:
        return Response({"error": str(e)}, status=500)