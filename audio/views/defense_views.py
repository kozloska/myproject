from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import datetime
from django.db.models import Exists, OuterRef, Q, Prefetch

from ..models import DefenseSchedule, Project, Protocol, CommissionComposition
from ..serializers import DefenseScheduleLiteSerializer, DefenseScheduleSerializer
from ..filters import DefenseScheduleFilter

class DefenseViewSet(viewsets.ModelViewSet):
    serializer_class = DefenseScheduleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DefenseScheduleFilter

    def get_queryset(self):
        now = timezone.now()
        start_of_year = timezone.make_aware(datetime(now.year, 1, 1, 0, 0, 0))
        end_of_year = timezone.make_aware(datetime(now.year, 12, 31, 23, 59, 59))
        
        # 🔥 ДОБАВЛЕНО: select_related для устранения N+1 проблемы
        queryset = DefenseSchedule.objects.select_related(
            'ID_Specialization',
            'ID_Commission'
        ).filter(
            DateTime__gte=start_of_year,
            DateTime__lte=end_of_year
        )
        
        return self.filterset_class(
            self.request.GET, 
            queryset=queryset, 
            request=self.request
        ).qs
    
    @action(detail=False, methods=['get'], url_path='with-pending-projects')
    def with_pending_projects(self, request):
        now = timezone.now()
        start_of_year = timezone.make_aware(datetime(now.year, 1, 1, 0, 0, 0))
        end_of_year = timezone.make_aware(datetime(now.year, 12, 31, 23, 59, 59))
        
        # 🔥 ДОБАВЛЕНО: select_related здесь тоже
        queryset = DefenseSchedule.objects.select_related(
            'ID_Specialization',
            'ID_Commission'
        ).filter(
            DateTime__gte=start_of_year,
            DateTime__lte=end_of_year
        )
        
        has_pending_work = Exists(
            Protocol.objects.filter(
                ID_DefenseSchedule=OuterRef('pk'),
                ID_Student__ID_Project__isnull=False,
                Status=False,
                Grade__isnull=False,
            )
        )
        queryset = queryset.filter(has_pending_work)
        filtered_queryset = self.filterset_class(
            request.GET, 
            queryset=queryset, 
            request=request
        ).qs
        
        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(filtered_queryset, many=True)
        return Response(serializer.data)
    

    