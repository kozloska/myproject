# audio/serializers.py
from rest_framework import serializers
from .models import AudioFile, Question, CommissionComposition, Specialization, Student, Project, Group, Institute, \
    SecretarySpecialization, User, Protocol, CommissionMember
from rest_framework import serializers
from .models import DefenseSchedule, Commission

class AudioFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioFile
        fields = ['audio']


class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = ['ID', 'Name']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['ID', 'Text', 'ID_Project']

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['ID', 'Title', 'Supervisor']