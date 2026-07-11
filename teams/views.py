from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Board,
    BoardAccess,
    Team,
    TeamMembership,
    accessible_boards,
    accessible_teams,
)
from .serializers import (
    AddMemberSerializer,
    BoardAccessSerializer,
    BoardSerializer,
    TeamMembershipSerializer,
    TeamSerializer,
)


class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return accessible_teams(self.request.user)

    def perform_create(self, serializer):
        # The creator becomes the owner and is recorded as an owner-membership.
        team = serializer.save(owner=self.request.user)
        TeamMembership.objects.get_or_create(
            team=team, user=self.request.user, defaults={'role': 'owner'}
        )

    def _require_owner(self, team):
        if team.owner_id != self.request.user.id:
            raise PermissionDenied('Only the team owner can do that.')

    def perform_destroy(self, instance):
        self._require_owner(instance)
        instance.delete()

    @action(detail=True, methods=['get', 'post'])
    def members(self, request, pk=None):
        team = self.get_object()

        if request.method == 'GET':
            members = team.memberships.select_related('user').all()
            return Response(TeamMembershipSerializer(members, many=True).data)

        # POST — owner adds a member by email (+ password if the account is new).
        self._require_owner(team)
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            user = data['existing_user']
            if user is None:
                user = User.objects.create_user(
                    username=data['email'],
                    email=data['email'],
                    password=data['password'],
                    first_name=data.get('name', '') or '',
                )
            membership, created = TeamMembership.objects.get_or_create(
                team=team, user=user, defaults={'role': 'member'}
            )

        return Response(
            TeamMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['delete'], url_path='members/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        team = self.get_object()
        self._require_owner(team)
        if str(team.owner_id) == str(user_id):
            raise PermissionDenied('The owner cannot be removed from the team.')
        TeamMembership.objects.filter(team=team, user_id=user_id).delete()
        BoardAccess.objects.filter(board__team=team, user_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BoardViewSet(viewsets.ModelViewSet):
    serializer_class = BoardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = accessible_boards(self.request.user)
        team_id = self.request.query_params.get('team')
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        return queryset

    def perform_create(self, serializer):
        team = serializer.validated_data['team']
        if team.owner_id != self.request.user.id:
            raise PermissionDenied('Only the team owner can create boards.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.team.owner_id != self.request.user.id:
            raise PermissionDenied('Only the team owner can delete boards.')
        instance.delete()

    @action(detail=True, methods=['get', 'post'])
    def access(self, request, pk=None):
        board = self.get_object()

        if request.method == 'GET':
            return Response(BoardAccessSerializer(board.access.all(), many=True).data)

        # POST — owner grants a team member access to this board.
        if board.team.owner_id != request.user.id:
            raise PermissionDenied('Only the team owner can grant board access.')
        user_id = request.data.get('user_id')
        member = TeamMembership.objects.filter(team=board.team, user_id=user_id).first()
        if member is None:
            return Response(
                {'detail': 'That user is not a member of this team.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        grant, created = BoardAccess.objects.get_or_create(board=board, user_id=user_id)
        return Response(
            BoardAccessSerializer(grant).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['delete'], url_path='access/(?P<user_id>[^/.]+)')
    def revoke_access(self, request, pk=None, user_id=None):
        board = self.get_object()
        if board.team.owner_id != request.user.id:
            raise PermissionDenied('Only the team owner can revoke board access.')
        BoardAccess.objects.filter(board=board, user_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
