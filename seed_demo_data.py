import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

from tasks.models import Tag, Task
from teams.models import Board, BoardAccess, Team, TeamMembership

User = get_user_model()

# --- Demo owner --------------------------------------------------------------
owner, _ = User.objects.get_or_create(
    username='demo',
    defaults={'email': 'demo@example.com', 'first_name': 'Demo', 'last_name': 'User'},
)
owner.set_password('demo12345')
owner.save()

# --- A second demo user (a teammate) ----------------------------------------
teammate, _ = User.objects.get_or_create(
    username='teammate@example.com',
    defaults={'email': 'teammate@example.com', 'first_name': 'Tess'},
)
teammate.set_password('teammate12345')
teammate.save()

# --- Team + membership -------------------------------------------------------
team, _ = Team.objects.get_or_create(name='Demo Team', owner=owner)
TeamMembership.objects.get_or_create(team=team, user=owner, defaults={'role': 'owner'})
TeamMembership.objects.get_or_create(team=team, user=teammate, defaults={'role': 'member'})

# --- Boards ------------------------------------------------------------------
board, _ = Board.objects.get_or_create(team=team, name='Product Roadmap')
design_board, _ = Board.objects.get_or_create(team=team, name='Design Sprint')

# Grant the teammate access to one board only (demonstrates per-board access).
BoardAccess.objects.get_or_create(board=board, user=teammate)

# --- Tags (team-scoped) ------------------------------------------------------
backend_tag, _ = Tag.objects.get_or_create(team=team, name='backend')
frontend_tag, _ = Tag.objects.get_or_create(team=team, name='frontend')

# --- Sample tasks on the first board ----------------------------------------
Task.objects.get_or_create(
    board=board,
    title='Set up authentication',
    defaults={
        'description': 'Complete the Django JWT login flow',
        'status': 'in_progress',
        'priority': 'high',
        'due_date': '2026-07-12',
        'order': 1,
        'created_by': owner,
    },
)
Task.objects.get_or_create(
    board=board,
    title='Review the kanban UI',
    defaults={
        'description': 'Check the task board layout and empty states',
        'status': 'todo',
        'priority': 'medium',
        'due_date': '2026-07-12',
        'order': 2,
        'created_by': owner,
    },
)
Task.objects.get_or_create(
    board=board,
    title='Ship the teams feature',
    defaults={
        'description': 'Owner-managed boards with per-board access',
        'status': 'done',
        'priority': 'low',
        'due_date': '2026-07-12',
        'order': 3,
        'created_by': owner,
    },
)

print('Seeded:')
print('  Owner    : demo@example.com / demo12345')
print('  Teammate : teammate@example.com / teammate12345 (access to "Product Roadmap")')
print(f'  Team     : {team.name} with boards: Product Roadmap, Design Sprint')
