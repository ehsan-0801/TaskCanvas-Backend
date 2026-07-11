import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def clear_task_data(apps, schema_editor):
    """Fresh start: existing user-owned tasks/tags are dropped so the columns can
    be re-pointed at boards/teams (non-nullable) without a data migration."""
    Task = apps.get_model('tasks', 'Task')
    Tag = apps.get_model('tasks', 'Tag')
    Task.tags.through.objects.all().delete()
    Task.objects.all().delete()
    Tag.objects.all().delete()


class Migration(migrations.Migration):

    # Non-atomic: on Postgres, clearing rows and then adding a NOT NULL column to
    # the same table in one transaction raises "pending trigger events". Running
    # each operation in its own transaction lets the delete commit first.
    atomic = False

    dependencies = [
        ('tasks', '0001_initial'),
        ('teams', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(clear_task_data, migrations.RunPython.noop),
        migrations.RemoveField(model_name='task', name='user'),
        migrations.RemoveField(model_name='tag', name='user'),
        migrations.AddField(
            model_name='tag',
            name='team',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tags',
                to='teams.team',
                default=None,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='task',
            name='board',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tasks',
                to='teams.board',
                default=None,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='task',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_tasks',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
