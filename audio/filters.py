import django_filters
from .models import CommissionMember, DefenseSchedule, Protocol, Project, Student
from django_filters import rest_framework as filters
from django_filters import rest_framework as filters

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


from django_filters import rest_framework as filters
from audio.models import Student, DefenseSchedule


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

