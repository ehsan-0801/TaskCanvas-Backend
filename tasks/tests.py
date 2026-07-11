from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Tag, Task


class TaskApiTestCase(APITestCase):
    """Shared setup: two users, each authenticated via JWT on demand."""

    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice", email="alice@example.com", password="secretpass123"
        )
        self.bob = User.objects.create_user(
            username="bob", email="bob@example.com", password="secretpass123"
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)


class TaskAuthTests(TaskApiTestCase):
    def test_requires_authentication(self):
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TaskCrudTests(TaskApiTestCase):
    def test_create_task(self):
        self.auth(self.alice)
        response = self.client.post(
            "/api/tasks/",
            {
                "title": "Write tests",
                "status": "todo",
                "priority": "high",
                "due_date": "2026-07-09",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Write tests")
        task = Task.objects.get(id=response.data["id"])
        self.assertEqual(task.user, self.alice)

    def test_create_task_with_tags(self):
        self.auth(self.alice)
        tag = Tag.objects.create(user=self.alice, name="backend")
        response = self.client.post(
            "/api/tasks/",
            {"title": "Tagged", "status": "todo", "priority": "low", "tag_ids": [tag.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["tags"]), 1)
        self.assertEqual(response.data["tags"][0]["name"], "backend")

    def test_create_task_missing_title_fails(self):
        self.auth(self.alice)
        response = self.client.post(
            "/api/tasks/", {"status": "todo", "priority": "low"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)

    def test_patch_task(self):
        self.auth(self.alice)
        task = Task.objects.create(user=self.alice, title="Old", status="todo")
        response = self.client.patch(
            f"/api/tasks/{task.id}/", {"title": "New"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.title, "New")

    def test_delete_task(self):
        self.auth(self.alice)
        task = Task.objects.create(user=self.alice, title="Doomed")
        response = self.client.delete(f"/api/tasks/{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(id=task.id).exists())


class TaskDateFilterTests(TaskApiTestCase):
    def test_list_filtered_by_date(self):
        self.auth(self.alice)
        Task.objects.create(user=self.alice, title="On date", due_date="2026-07-09")
        Task.objects.create(user=self.alice, title="Other date", due_date="2026-07-10")
        response = self.client.get("/api/tasks/", {"date": "2026-07-09"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [t["title"] for t in response.data["results"]]
        self.assertEqual(titles, ["On date"])

    def test_list_without_date_returns_all(self):
        self.auth(self.alice)
        Task.objects.create(user=self.alice, title="A", due_date="2026-07-09")
        Task.objects.create(user=self.alice, title="B", due_date="2026-07-10")
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.data["count"], 2)


class TaskIsolationTests(TaskApiTestCase):
    def test_list_only_returns_own_tasks(self):
        Task.objects.create(user=self.alice, title="Alice task")
        Task.objects.create(user=self.bob, title="Bob task")
        self.auth(self.alice)
        response = self.client.get("/api/tasks/")
        titles = [t["title"] for t in response.data["results"]]
        self.assertEqual(titles, ["Alice task"])

    def test_cannot_read_another_users_task(self):
        bob_task = Task.objects.create(user=self.bob, title="Bob task")
        self.auth(self.alice)
        response = self.client.get(f"/api/tasks/{bob_task.id}/")
        # Not visible to Alice — must 404, never leak existence.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_another_users_task(self):
        bob_task = Task.objects.create(user=self.bob, title="Bob task")
        self.auth(self.alice)
        response = self.client.delete(f"/api/tasks/{bob_task.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Task.objects.filter(id=bob_task.id).exists())


class TaskReorderTests(TaskApiTestCase):
    def test_reorder_updates_status_and_order(self):
        self.auth(self.alice)
        t1 = Task.objects.create(user=self.alice, title="1", status="todo", order=0)
        t2 = Task.objects.create(user=self.alice, title="2", status="todo", order=1)
        response = self.client.post(
            "/api/tasks/reorder/",
            {
                "updates": [
                    {"id": t1.id, "status": "in_progress", "order": 0},
                    {"id": t2.id, "status": "todo", "order": 0},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        t1.refresh_from_db()
        t2.refresh_from_db()
        self.assertEqual(t1.status, "in_progress")
        self.assertEqual(t2.order, 0)

    def test_reorder_ignores_other_users_tasks(self):
        self.auth(self.alice)
        bob_task = Task.objects.create(user=self.bob, title="Bob", status="todo", order=5)
        response = self.client.post(
            "/api/tasks/reorder/",
            {"updates": [{"id": bob_task.id, "status": "done", "order": 0}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bob_task.refresh_from_db()
        # Bob's task must be untouched.
        self.assertEqual(bob_task.status, "todo")
        self.assertEqual(bob_task.order, 5)


class TagTests(TaskApiTestCase):
    def test_create_and_list_tags_scoped_to_user(self):
        self.auth(self.alice)
        self.client.post("/api/tasks/tags/", {"name": "backend"}, format="json")
        Tag.objects.create(user=self.bob, name="bob-only")
        response = self.client.get("/api/tasks/tags/")
        names = [t["name"] for t in response.data["results"]]
        self.assertEqual(names, ["backend"])
