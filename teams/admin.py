from django.contrib import admin

from .models import Board, BoardAccess, Team, TeamMembership

admin.site.register(Team)
admin.site.register(TeamMembership)
admin.site.register(Board)
admin.site.register(BoardAccess)
