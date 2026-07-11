import calendar
import os
from datetime import date

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

from tasks.models import Tag, Task
from teams.models import Board, BoardAccess, Team, TeamMembership

User = get_user_model()

# A rotating set of realistic task titles for the month's To Do column.
TASK_TEMPLATES = [
    "Plan the sprint",
    "Review pull requests",
    "Write documentation",
    "Fix reported bugs",
    "Design review",
    "Team standup notes",
    "Update dependencies",
    "Refine the backlog",
    "Customer feedback triage",
    "Prepare the demo",
]
PRIORITIES = ["low", "medium", "high"]


def make_user(email, password, first_name=""):
    """Create-or-update a user keyed by email (used as the username)."""
    user, _ = User.objects.get_or_create(
        username=email, defaults={"email": email, "first_name": first_name}
    )
    user.email = email
    if first_name:
        user.first_name = first_name
    user.set_password(password)
    user.save()
    return user


def seed_month_of_todos(board, created_by, tags):
    """Fill a board's To Do column with one task per day of the current month."""
    today = date.today()
    year, month = today.year, today.month
    days_in_month = calendar.monthrange(year, month)[1]

    for day in range(1, days_in_month + 1):
        due = date(year, month, day)
        label = TASK_TEMPLATES[(day - 1) % len(TASK_TEMPLATES)]
        title = f"{label} ({due.strftime('%b %d')})"
        task, created = Task.objects.get_or_create(
            board=board,
            due_date=due,
            title=title,
            defaults={
                "status": "todo",
                "priority": PRIORITIES[(day - 1) % len(PRIORITIES)],
                "order": day,
                "created_by": created_by,
                "description": "",
            },
        )
        if created and tags:
            task.tags.set([tags[(day - 1) % len(tags)]])


def build_owner(owner_email, owner_password, owner_name, member_specs, team_names):
    """Create an owner with members, two teams (each with a board of monthly
    To Do tasks), and grant every member access to every board."""
    owner = make_user(owner_email, owner_password, owner_name)
    members = [make_user(email, pw, name) for (email, pw, name) in member_specs]

    for team_name in team_names:
        team, _ = Team.objects.get_or_create(name=team_name, owner=owner)
        TeamMembership.objects.get_or_create(team=team, user=owner, defaults={"role": "owner"})

        backend_tag, _ = Tag.objects.get_or_create(team=team, name="backend")
        frontend_tag, _ = Tag.objects.get_or_create(team=team, name="frontend")

        board, _ = Board.objects.get_or_create(team=team, name=f"{team_name} Board")

        for member in members:
            TeamMembership.objects.get_or_create(team=team, user=member, defaults={"role": "member"})
            BoardAccess.objects.get_or_create(board=board, user=member)

        seed_month_of_todos(board, owner, [backend_tag, frontend_tag])

    return owner, members


# --- Owner 1 -----------------------------------------------------------------
build_owner(
    owner_email="demo@example.com",
    owner_password="demo12345",
    owner_name="Demo Owner",
    member_specs=[
        ("alice@example.com", "member12345", "Alice"),
        ("bob@example.com", "member12345", "Bob"),
        ("carol@example.com", "member12345", "Carol"),
        ("dave@example.com", "member12345", "Dave"),
    ],
    team_names=["Acme Product", "Acme Marketing"],
)

# --- Owner 2 -----------------------------------------------------------------
build_owner(
    owner_email="owner2@example.com",
    owner_password="owner212345",
    owner_name="Second Owner",
    member_specs=[
        ("erin@example.com", "member12345", "Erin"),
        ("frank@example.com", "member12345", "Frank"),
        ("grace@example.com", "member12345", "Grace"),
        ("heidi@example.com", "member12345", "Heidi"),
    ],
    team_names=["Globex Engineering", "Globex Design"],
)

_days = calendar.monthrange(date.today().year, date.today().month)[1]
print("Seeded 2 owners, each with 4 members, 2 teams, and a board per team.")
print(f"Each board holds {_days} To Do tasks (one per day of the current month).")
print()
print("Owners:")
print("  demo@example.com   / demo12345     (teams: Acme Product, Acme Marketing)")
print("  owner2@example.com / owner212345   (teams: Globex Engineering, Globex Design)")
print("Members (all): password 'member12345'")
print("  alice, bob, carol, dave  @example.com   -> Demo Owner's teams")
print("  erin, frank, grace, heidi @example.com  -> Second Owner's teams")
