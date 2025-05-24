import django_filters
from .models import CommissionMember, DefenseSchedule, Protocol, Project, Student, Commission
from django_filters import rest_framework as filters
from audio.models import Student, DefenseSchedule
from django.db.models import Q
from .models import Protocol


class SecretaryFilter(django_filters.FilterSet):
    Surname = django_filters.CharFilter(field_name='Surname', lookup_expr='icontains')
    Name = django_filters.CharFilter(field_name='Name', lookup_expr='icontains')
    Patronymic = django_filters.CharFilter(field_name='Patronymic', lookup_expr='icontains')

    class Meta:
        model = CommissionMember
        fields = '__all__'

class DefenseScheduleFilter(django_filters.FilterSet):
    specialization_id = django_filters.NumberFilter(
        method='filter_by_specialization',
        label='ID специализации'
    )

    class Meta:
        model = DefenseSchedule
        fields = []

    def filter_by_specialization(self, queryset, name, value):
        return queryset.filter(
            protocol__ID_Student__ID_Specialization=value
        ).distinct('ID')



class ProjectFilter(django_filters.FilterSet):
    defense_schedule_id = django_filters.NumberFilter(
        method='filter_by_defense_schedule',
        label='ID расписания защиты'
    )

    class Meta:
        model = Project
        fields = []

    def filter_by_defense_schedule(self, queryset, name, value):
        return queryset.filter(
            student__protocol__ID_DefenseSchedule=value
        ).distinct()



class StudentFilter(filters.FilterSet):
    grade = filters.CharFilter(
        field_name='protocol__Grade',
        lookup_expr='exact',
        label='Grade'
    )

    class Meta:
        model = Student
        fields = {
            'ID_Project': ['exact'],
            'ID_Group': ['exact'],
            'ID_Specialization': ['exact'],  # Фильтрация остается, но поле не выводится
        }

from django_filters import rest_framework as filters

class CommissionFilter(filters.FilterSet):
    id_member = filters.NumberFilter(field_name='commissioncomposition__ID_Member')
    role = filters.CharFilter(field_name='commissioncomposition__Role')

    class Meta:
        model = Commission
        fields = ['ID', 'Name']  # Указываем только поля модели Commission

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        # Применяем фильтры одновременно, если оба указаны
        if self.data.get('id_member') and self.data.get('role'):
            return queryset.filter(
                commissioncomposition__ID_Member=self.data['id_member'],
                commissioncomposition__Role=self.data['role']
            ).distinct()
        return queryset



class ProtocolFilter(django_filters.FilterSet):
    student_fio = django_filters.CharFilter(method='filter_by_student_fio')

    class Meta:
        model = Protocol
        fields = ['ID_Student', 'Status', 'Year']

    def filter_by_student_fio(self, queryset, name, value):
        if not value:
            return queryset

        # Убираем лишние пробелы и разбиваем на слова
        words = value.strip().split()

        # Создаем условия для каждого слова (ИЛИ между словами)
        q_objects = Q()
        for word in words:
            q_objects |= (
                    Q(ID_Student__Surname__icontains=word) |
                    Q(ID_Student__Name__icontains=word) |
                    Q(ID_Student__Patronymic__icontains=word)
            )

        return queryset.filter(q_objects)