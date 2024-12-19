# audio/serializers.py
from rest_framework import serializers
from .models import AudioFile, Question
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

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['ID', 'Text', 'ID_Project']  # Укажите поля, которые хотите сериализовать

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = ['ID', 'Title', 'Supervisor']  # Укажите нужные поля