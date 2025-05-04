import django_filters
from .models import CommissionMember

class SecretaryFilter(django_filters.FilterSet):
    Surname = django_filters.CharFilter(field_name='Surname', lookup_expr='icontains')
    Name = django_filters.CharFilter(field_name='Name', lookup_expr='icontains')
    Patronymic = django_filters.CharFilter(field_name='Patronymic', lookup_expr='icontains')

    class Meta:
        model = CommissionMember
        fields = '__all__'
