from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Tag, Task
from .serializers import TagSerializer, TaskSerializer


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Task.objects.filter(user=self.request.user).prefetch_related('tags')
        due_date = self.request.query_params.get('date')
        if due_date:
            queryset = queryset.filter(due_date=due_date)
        return queryset.order_by('status', 'order', 'created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        updates = request.data.get('updates', [])
        with transaction.atomic():
            for update in updates:
                task = Task.objects.filter(user=request.user, id=update.get('id')).first()
                if task is None:
                    continue
                task.status = update.get('status', task.status)
                task.order = update.get('order', task.order)
                task.save(update_fields=['status', 'order'])
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)
