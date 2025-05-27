from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from ..models import DefenseSchedule
from ..serializers import DefenseScheduleSerializer
from ..filters import DefenseScheduleFilter
from django.utils import timezone
from datetime import datetime
from django.utils import timezone
from rest_framework import viewsets

class DefenseViewSet(viewsets.ModelViewSet):
    queryset = DefenseSchedule.objects.all()
    serializer_class = DefenseScheduleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DefenseScheduleFilter

    def get_queryset(self):
        # Текущая дата и время с учётом часового поюза
        now = timezone.now()
        # Начало текущего дня (00:00:00)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # Конец текущего года (31 декабря 23:59:59)
        end_of_year = datetime(now.year, 12, 31, 23, 59, 59)
        end_of_year = timezone.make_aware(end_of_year)

        # Фильтруем записи по диапазону дат
        queryset = DefenseSchedule.objects.filter(
            DateTime__gte=start_of_day,
            DateTime__lte=end_of_year
        )

        # Применяем дополнительные фильтры
        return self.filterset_class(self.request.GET, queryset=queryset, request=self.request).qs