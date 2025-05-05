import django_filters
from .models import CommissionMember, DefenseSchedule, Protocol


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


