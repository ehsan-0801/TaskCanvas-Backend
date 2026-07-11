from django.urls import path

from .views import BoardViewSet, TeamViewSet

team_list = TeamViewSet.as_view({'get': 'list', 'post': 'create'})
team_detail = TeamViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'})
team_members = TeamViewSet.as_view({'get': 'members', 'post': 'members'})
team_remove_member = TeamViewSet.as_view({'delete': 'remove_member'})

board_list = BoardViewSet.as_view({'get': 'list', 'post': 'create'})
board_detail = BoardViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'})
board_access = BoardViewSet.as_view({'get': 'access', 'post': 'access'})
board_revoke = BoardViewSet.as_view({'delete': 'revoke_access'})

urlpatterns = [
    path('teams/', team_list, name='team-list'),
    path('teams/<int:pk>/', team_detail, name='team-detail'),
    path('teams/<int:pk>/members/', team_members, name='team-members'),
    path('teams/<int:pk>/members/<int:user_id>/', team_remove_member, name='team-remove-member'),
    path('boards/', board_list, name='board-list'),
    path('boards/<int:pk>/', board_detail, name='board-detail'),
    path('boards/<int:pk>/access/', board_access, name='board-access'),
    path('boards/<int:pk>/access/<int:user_id>/', board_revoke, name='board-revoke-access'),
]
