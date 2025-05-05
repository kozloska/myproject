# audio/serializers.py
from rest_framework import serializers
from .models import (
    AudioFile,
    Commission,
    CommissionMember,
    DefenseSchedule,
    Group,
    Institute,
    Project,
    Specialization,
    Student,
    Question,
    Protocol,
    CommissionComposition,
    SecretarySpecialization,
    User,
)

class AudioFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioFile
        fields = ['audio']

class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = '__all__'

class CommissionMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionMember
        fields = '__all__'

class DefenseScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefenseSchedule
        fields = '__all__'

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'

class InstituteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institute
        fields = '__all__'

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'

class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = '__all__'

class StudentSerializer(serializers.ModelSerializer):
    ID_Group = GroupSerializer(read_only=True)
    class Meta:
        model = Student
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

class ProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Protocol
        fields = '__all__'

class CommissionCompositionSerializer(serializers.ModelSerializer):
    ID_Commission = CommissionSerializer(read_only=True)
    class Meta:
        model = CommissionComposition
        fields = '__all__'

class SecretarySpecializationSerializer(serializers.ModelSerializer):
    ID_Specialization = SpecializationSerializer(read_only=True)
    class Meta:
        model = SecretarySpecialization
        fields = ['ID', 'ID_Specialization']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class UpdateGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Protocol
        fields = ['ID_Student', 'Grade']


class UpdateDefenseTimeByProjectSerializer(serializers.ModelSerializer):
    ID_Project = serializers.IntegerField(write_only=True)  # Явно указываем, что это входной параметр

    class Meta:
        model = Protocol
        fields = ['ID_Project', 'DefenseStartTime']
        extra_kwargs = {
            'DefenseStartTime': {'required': True}
        }

    def validate_ID_Project(self, value):
        if not Student.objects.filter(ID_Project=value).exists():
            raise serializers.ValidationError("Студенты с таким ID проекта не найдены")
        return value

