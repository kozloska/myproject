from django.core.files.storage import default_storage
from rest_framework import serializers
from .models import (
    AudioFile,
    Commission,
    CommissionMember,
    DefenseSchedule,
    Group,
    Project,
    Specialization,
    Student,
    Question,
    Protocol,
    CommissionComposition,
    SecretarySpecialization,
    Qualification
)

class AudioUploadSerializer(serializers.Serializer):
    audio = serializers.FileField(required=True)
    project_id = serializers.IntegerField(required=True)

    def validate(self, validated_data):
        project_id = validated_data.get('project_id')
        if not project_id:
            raise serializers.ValidationError("project_id is required")
        return validated_data

    def save(self):
        audio_file = self.validated_data['audio']
        project_id = self.validated_data['project_id']
        # Сохраняем файл временно
        file_path = default_storage.save(f"audio/{audio_file.name}", audio_file)
        return {'file_path': default_storage.path(file_path), 'project_id': project_id}


class CommissionMemberSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CommissionMember
        # 🔑 Уберите 'last_login' отсюда, если он не нужен фронтенду
        fields = ['ID', 'login', 'Surname', 'Name', 'Patronymic', 'full_name', 'is_active']
        read_only_fields = fields

    def get_full_name(self, obj):
        return f"{obj.Surname} {obj.Name} {obj.Patronymic}".strip()

class CommissionMemberShortSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CommissionMember
        fields = ['ID', 'Surname', 'Name', 'Patronymic', 'full_name', 'login']

    def get_full_name(self, obj):
        return f"{obj.Surname} {obj.Name} {obj.Patronymic}".strip()


class CommissionCompositionSerializer(serializers.ModelSerializer):
    # При чтении показываем полные данные участника
    ID_Member = CommissionMemberShortSerializer(read_only=True)
    
    # При записи принимаем ID участника
    member_id = serializers.PrimaryKeyRelatedField(
        source='ID_Member',
        queryset=CommissionMember.objects.all(),
        write_only=True
    )

    class Meta:
        model = CommissionComposition
        fields = ['ID', 'ID_Commission', 'ID_Member', 'member_id', 'Role']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Удаляем write_only поле из ответа, если оно там осталось
        ret.pop('member_id', None)
        return ret
    
class Commission_CompositionSerializer(serializers.ModelSerializer):
    ID_Member = serializers.PrimaryKeyRelatedField(queryset=CommissionMember.objects.all())

    class Meta:
        model = CommissionComposition
        fields = '__all__'

    def to_representation(self, instance):
        # Получаем стандартное представление
        representation = super().to_representation(instance)
        # Заменяем ID на полный объект CommissionMember
        representation['ID_Member'] = CommissionMemberSerializer(instance.ID_Member).data
        return representation

class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = '__all__'

class QualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Qualification
        fields = '__all__'
        
class SecretarySpecializationSerializer(serializers.ModelSerializer): 
    # === ДЛЯ ЧТЕНИЯ (выводим полные данные специализации) ===
    ID_Specialization = serializers.SerializerMethodField()
    ID_Secretary = CommissionMemberShortSerializer(read_only=True)  # или ваш serializer для члена комиссии
    
    # === ДЛЯ ЗАПИСИ (принимаем только ID) ===
    # Важно: имя поля должно отличаться от read-only поля!
    id_specialization = serializers.PrimaryKeyRelatedField(
        source='ID_Specialization',  # связываем с модельным полем
        queryset=Specialization.objects.all(),
        write_only=True
    )
    id_secretary = serializers.PrimaryKeyRelatedField(
        source='ID_Secretary',
        queryset=CommissionMember.objects.all(),
        write_only=True
    )

    class Meta:
        model = SecretarySpecialization
        fields = [
            'ID', 
            'ID_Specialization',  # read-only (объект)
            'ID_Secretary',       # read-only (объект)
            'id_specialization',  # write-only (ID)
            'id_secretary'        # write-only (ID)
        ]

    def get_ID_Specialization(self, obj):
        if obj.ID_Specialization:
            return SpecializationSerializer(obj.ID_Specialization).data
        return None
    
    def to_representation(self, instance):
        # Убираем write_only поля из ответа клиенту
        ret = super().to_representation(instance)
        ret.pop('id_specialization', None)
        ret.pop('id_secretary', None)
        return ret

class CommissionSerializer(serializers.ModelSerializer):
    members = CommissionCompositionSerializer(many=True, read_only=True, source='commissioncomposition_set')
    class Meta:
        model = Commission
        fields = '__all__'


class DefenseScheduleSerializer(serializers.ModelSerializer):
    ID_Commission = serializers.PrimaryKeyRelatedField(
        queryset=Commission.objects.all(),
        required=False  
    )
    class Meta:
        model = DefenseSchedule
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.ID_Commission:
            data['ID_Commission'] = CommissionSerializer(instance.ID_Commission).data 
        return data


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
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
    ID_Student = StudentSerializer(read_only=True)
    
    class Meta:
        model = Protocol
        fields = '__all__'  
        
    def to_representation(self, instance):
        # Сначала получаем стандартное представление (где ID_DefenseSchedule - это просто число)
        data = super().to_representation(instance)
        
        # Если расписание назначено, заменяем ID на полный объект
        if instance.ID_DefenseSchedule:
            data['ID_DefenseSchedule'] = DefenseScheduleSerializer(instance.ID_DefenseSchedule).data
            
        return data  

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

class FIOSerializer(serializers.Serializer):
    fio = serializers.CharField(max_length=255, required=True)
    dative_fio = serializers.CharField(max_length=255, read_only=True)

# 1. Для входа (только логин и пароль)
class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True) # write_only значит, что он не вернется в ответе

# 2. Для отображения данных пользователя (без пароля!)
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CommissionMember
        fields = ['ID', 'login', 'Surname', 'Name', 'Patronymic', 'full_name', 'is_active']
        read_only_fields = fields

    def get_full_name(self, obj):
        return f"{obj.Surname} {obj.Name} {obj.Patronymic}"
    
# === ЛЕГКИЕ СЕРИАЛИЗАТОРЫ ДЛЯ ТАБЛИЦЫ ===

class GroupLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['ID', 'Name']

class SpecializationLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ['ID', 'Name']

class ProjectLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['ID', 'Title', 'Supervisor']

class StudentArchiveLiteSerializer(serializers.ModelSerializer):
    ID_Group = GroupLiteSerializer(read_only=True)
    ID_Specialization = SpecializationLiteSerializer(read_only=True)
    ID_Project = ProjectLiteSerializer(read_only=True)
    
    class Meta:
        model = Student
        fields = ['ID', 'Surname', 'Name', 'Patronymic', 'ID_Group', 'ID_Specialization', 'ID_Project']

class DefenseScheduleArchiveLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefenseSchedule
        fields = ['ID', 'DateTime']

class ProtocolArchiveLiteSerializer(serializers.ModelSerializer):
    ID_Student = StudentArchiveLiteSerializer(read_only=True)
    ID_DefenseSchedule = DefenseScheduleArchiveLiteSerializer(read_only=True)
    
    class Meta:
        model = Protocol
        fields = [
            'ID', 'Number', 'Year', 'Grade', 'Status',
            'ID_Student', 'ID_DefenseSchedule',
            'ID_Question', 'ID_Question2',
            'DefenseStartTime', 'DefenseEndTime'
        ]

class DefenseScheduleLiteSerializer(serializers.ModelSerializer):
    ID_Specialization = serializers.SerializerMethodField()
    
    class Meta:
        model = DefenseSchedule
        fields = ['ID', 'DateTime', 'Class', 'Count', 'ID_Specialization']
    
    def get_ID_Specialization(self, obj):
        if obj.ID_Specialization:
            return {
                'ID': obj.ID_Specialization.ID,
                'Name': obj.ID_Specialization.Name
            }
        return None