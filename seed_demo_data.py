import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from tasks.models import Tag, Task

User = get_user_model()

user, created = User.objects.get_or_create(
    username='demo',
    defaults={
        'email': 'demo@example.com',
        'first_name': 'Demo',
        'last_name': 'User',
    },
)
if created:
    user.set_password('demo12345')
    user.save()
else:
    user.set_password('demo12345')
    user.save()

backend_tag, _ = Tag.objects.get_or_create(user=user, name='backend')
frontend_tag, _ = Tag.objects.get_or_create(user=user, name='frontend')

Task.objects.get_or_create(
    user=user,
    title='Set up authentication',
    defaults={
        'description': 'Complete the Django JWT login flow',
        'status': 'in_progress',
        'priority': 'high',
        'due_date': '2026-07-05',
        'order': 1,
    },
)
Task.objects.get_or_create(
    user=user,
    title='Review the kanban UI',
    defaults={
        'description': 'Check the task board layout and empty states',
        'status': 'todo',
        'priority': 'medium',
        'due_date': '2026-07-05',
        'order': 2,
    },
)
Task.objects.get_or_create(
    user=user,
    title='Upload an image for annotation',
    defaults={
        'description': 'Test image upload and polygon drawing',
        'status': 'done',
        'priority': 'low',
        'due_date': '2026-07-05',
        'order': 3,
    },
)

print('Demo user created/updated: demo@example.com / demo12345')
