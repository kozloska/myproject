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
)

class AudioUploadSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = AudioFile
        fields = ['audio', 'project_id']
        extra_kwargs = {
            'audio': {'required': True}
        }

    def create(self, validated_data):
        project_id = validated_data.pop('project_id')
        audio_file = AudioFile.objects.create(**validated_data)
        self.context['project_id'] = project_id
        return audio_file

class CommissionMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionMember
        fields = '__all__'

class CommissionCompositionSerializer(serializers.ModelSerializer):
    ID_Member = CommissionMemberSerializer(read_only=True)
    class Meta:
        model = CommissionComposition
        fields = '__all__'

class Commission_CompositionSerializer(serializers.ModelSerializer):
    ID_Member = CommissionMemberSerializer()
    class Meta:
        model = CommissionComposition
        fields = '__all__'

class CommissionSerializer(serializers.ModelSerializer):
    members = CommissionCompositionSerializer(many=True, read_only=True, source='commissioncomposition_set')
    class Meta:
        model = Commission
        fields = '__all__'


class DefenseScheduleSerializer(serializers.ModelSerializer):
    ID_Commission = CommissionSerializer()
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
    grade = serializers.SerializerMethodField()
    ID_Specialization = SpecializationSerializer(read_only=True)
    ID_Project = ProjectSerializer(read_only=True)
    class Meta:
        model = Student
        fields = '__all__'

    def get_grade(self, obj):
        last_protocol = obj.protocol_set.order_by('-ID').first()
        return last_protocol.Grade if last_protocol else None

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

class ProtocolSerializer(serializers.ModelSerializer):
    ID_Student = StudentSerializer()
    ID_DefenseSchedule = DefenseScheduleSerializer()
    class Meta:
        model = Protocol
        fields = '__all__'


class SecretarySpecializationSerializer(serializers.ModelSerializer):
    ID_Specialization = SpecializationSerializer(read_only=True)
    class Meta:
        model = SecretarySpecialization
        fields = ['ID', 'ID_Specialization']


class UpdateGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Protocol
        fields = ['ID_Student', 'Grade']


class UpdateDefenseTimeByProjectSerializer(serializers.ModelSerializer):
    ID_Project = serializers.IntegerField(write_only=True)

    class Meta:
        model = Protocol
        fields = ['ID_Project', 'DefenseStartTime']
        extra_kwargs = {
            'DefenseStartTime': {
                'required': False,
                'allow_null': True
            }
        }

    def validate_ID_Project(self, value):
        if not Student.objects.filter(ID_Project=value).exists():
            raise serializers.ValidationError("Студенты с таким ID проекта не найдены")
        return value


class TodayDefenseQuerySerializer(serializers.Serializer):
    specialization_id = serializers.IntegerField(
        required=True,
        help_text="ID специализации для фильтрации защит",
        min_value=1
    )

    def validate_specialization_id(self, value):
        if not Specialization.objects.filter(ID=value).exists():
            raise serializers.ValidationError("Специализация с таким ID не найдена")
        return value


class UpdateDefenseTimeEndByProjectSerializer(serializers.ModelSerializer):
    ID_Project = serializers.IntegerField(write_only=True)

    class Meta:
        model = Protocol
        fields = ['ID_Project', 'DefenseEndTime']
        extra_kwargs = {
            'DefenseEndTime': {
                'required': False,
                'allow_null': True
            }
        }

    def validate_ID_Project(self, value):
        if not Student.objects.filter(ID_Project=value).exists():
            raise serializers.ValidationError("Студенты с таким ID проекта не найдены")
        return value

