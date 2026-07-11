from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from teams.models import accessible_boards, accessible_teams, user_can_access_board

from .models import Tag, Task
from .serializers import TagSerializer, TaskSerializer


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        teams = accessible_teams(self.request.user)
        queryset = Tag.objects.filter(team__in=teams)
        team_id = self.request.query_params.get('team')
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        return queryset

    def perform_create(self, serializer):
        team = serializer.validated_data.get('team')
        if team not in accessible_teams(self.request.user):
            raise PermissionDenied('You are not a member of that team.')
        serializer.save()


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        boards = accessible_boards(self.request.user)
        queryset = Task.objects.filter(board__in=boards).prefetch_related('tags')
        board_id = self.request.query_params.get('board')
        if board_id:
            queryset = queryset.filter(board_id=board_id)
        due_date = self.request.query_params.get('date')
        if due_date:
            queryset = queryset.filter(due_date=due_date)
        return queryset.order_by('status', 'order', 'created_at')

    def perform_create(self, serializer):
        board = serializer.validated_data.get('board')
        if board is None or not user_can_access_board(self.request.user, board):
            raise PermissionDenied('You do not have access to that board.')
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        updates = request.data.get('updates', [])
        boards = accessible_boards(request.user)
        with transaction.atomic():
            for update in updates:
                # Only reorder tasks on boards the user can access.
                task = Task.objects.filter(board__in=boards, id=update.get('id')).first()
                if task is None:
                    continue
                task.status = update.get('status', task.status)
                task.order = update.get('order', task.order)
                task.save(update_fields=['status', 'order'])
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)
