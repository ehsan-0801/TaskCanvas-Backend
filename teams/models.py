from django.conf import settings
from django.db import models
from django.db.models import Q


class Team(models.Model):
    """A group owned by one user. The owner can create boards and add members."""

    name = models.CharField(max_length=120)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_teams'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    ROLE_CHOICES = [('owner', 'Owner'), ('member', 'Member')]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_memberships'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('team', 'user')
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user} in {self.team} ({self.role})'


class Board(models.Model):
    """A Kanban board belonging to a team. A team can have many boards."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='boards')
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.name


class BoardAccess(models.Model):
    """Grants a specific (non-owner) user access to a specific board."""

    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='access')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='board_access'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('board', 'user')


# --- Access helpers: the single source of truth for who can see/do what --------

def accessible_teams(user):
    """Teams the user owns or is a member of."""
    return Team.objects.filter(Q(owner=user) | Q(memberships__user=user)).distinct()


def accessible_boards(user):
    """Boards the user can see: every board of a team they own, plus any board
    they've been explicitly granted access to."""
    return Board.objects.filter(
        Q(team__owner=user) | Q(access__user=user)
    ).distinct()


def user_owns_team(user, team):
    return team.owner_id == user.id


def user_can_access_board(user, board):
    return board.team.owner_id == user.id or board.access.filter(user=user).exists()
