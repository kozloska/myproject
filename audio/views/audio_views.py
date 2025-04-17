from django.core.files.storage import default_storage
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import os
from ..models import AudioFile, Project
from ..serializers import AudioFileSerializer
from ..services.audio_service import AudioService
from ..services.transcription_service import TranscriptionService
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
def upload_audio(request):
    logger.info("Audio upload request received")

    serializer = AudioFileSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        audio_file = serializer.save()
        project_id = request.data.get('project_id')

        if not project_id:
            return Response({"error": "Project ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        AudioService.validate_audio_file(audio_file.audio.name)
        audio_file_path = default_storage.path(audio_file.audio.name)

        if not os.path.exists(audio_file_path):
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)

        # Convert to WAV if needed
        if not audio_file.audio.name.endswith('.wav'):
            converted_path = audio_file_path.replace(os.path.splitext(audio_file.audio.name)[1], '.wav')
            AudioService.convert_to_wav(audio_file_path, converted_path)
            audio_file_path = converted_path

        # Transcribe audio
        transcribed_text = AudioService.transcribe_audio(audio_file_path)
        questions = TranscriptionService.extract_questions(transcribed_text)
        TranscriptionService.save_questions(questions, project_id)

        return Response({"message": "Audio processed successfully"}, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)