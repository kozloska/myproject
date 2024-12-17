# audio/serializers.py
from rest_framework import serializers
from .models import AudioFile
from rest_framework import serializers
from .models import DefenseSchedule, Commission

class AudioFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioFile
        fields = ['audio']



class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = ['ID', 'Name']  # Укажите нужные поля


