from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from teams.models import Board, BoardAccess, Team, TeamMembership

from .models import Tag, Task


class BoardTaskTestCase(APITestCase):
    """Owner with a board, plus a member granted access to it, and an outsider."""

    def setUp(self):
        self.owner = User.objects.create_user('owner', 'owner@example.com', 'secretpass123')
        self.member = User.objects.create_user('member', 'member@example.com', 'secretpass123')
        self.outsider = User.objects.create_user('out', 'out@example.com', 'secretpass123')

        self.team = Team.objects.create(name='Acme', owner=self.owner)
        TeamMembership.objects.create(team=self.team, user=self.owner, role='owner')
        TeamMembership.objects.create(team=self.team, user=self.member, role='member')
        self.board = Board.objects.create(team=self.team, name='Sprint')
        self.other_board = Board.objects.create(team=self.team, name='Secret')
        BoardAccess.objects.create(board=self.board, user=self.member)

    def auth(self, user):
        self.client.force_authenticate(user=user)


class TaskAuthTests(BoardTaskTestCase):
    def test_requires_authentication(self):
        self.assertEqual(self.client.get('/api/tasks/').status_code, status.HTTP_401_UNAUTHORIZED)


class TaskCrudTests(BoardTaskTestCase):
    def test_owner_creates_task_on_board(self):
        self.auth(self.owner)
        r = self.client.post(
            '/api/tasks/',
            {'board': self.board.id, 'title': 'Write tests', 'status': 'todo', 'priority': 'high'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(id=r.data['id'])
        self.assertEqual(task.board, self.board)
        self.assertEqual(task.created_by, self.owner)

    def test_member_can_create_on_granted_board(self):
        self.auth(self.member)
        r = self.client.post(
            '/api/tasks/', {'board': self.board.id, 'title': 'Member task', 'status': 'todo', 'priority': 'low'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_member_cannot_create_on_ungranted_board(self):
        self.auth(self.member)
        r = self.client.post(
            '/api/tasks/', {'board': self.other_board.id, 'title': 'Nope', 'status': 'todo', 'priority': 'low'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_outsider_cannot_create(self):
        self.auth(self.outsider)
        r = self.client.post(
            '/api/tasks/', {'board': self.board.id, 'title': 'Hax', 'status': 'todo', 'priority': 'low'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_title_fails(self):
        self.auth(self.owner)
        r = self.client.post('/api/tasks/', {'board': self.board.id, 'status': 'todo', 'priority': 'low'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


class TaskVisibilityTests(BoardTaskTestCase):
    def test_list_filtered_by_board(self):
        Task.objects.create(board=self.board, title='A')
        Task.objects.create(board=self.other_board, title='B')
        self.auth(self.owner)
        r = self.client.get(f'/api/tasks/?board={self.board.id}')
        titles = [t['title'] for t in r.data['results']]
        self.assertEqual(titles, ['A'])

    def test_member_only_sees_granted_board_tasks(self):
        Task.objects.create(board=self.board, title='Visible')
        Task.objects.create(board=self.other_board, title='Hidden')
        self.auth(self.member)
        r = self.client.get('/api/tasks/')
        titles = [t['title'] for t in r.data['results']]
        self.assertEqual(titles, ['Visible'])

    def test_member_cannot_read_ungranted_task(self):
        hidden = Task.objects.create(board=self.other_board, title='Hidden')
        self.auth(self.member)
        r = self.client.get(f'/api/tasks/{hidden.id}/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_date_filter(self):
        Task.objects.create(board=self.board, title='On', due_date='2026-07-11')
        Task.objects.create(board=self.board, title='Off', due_date='2026-07-12')
        self.auth(self.owner)
        r = self.client.get(f'/api/tasks/?board={self.board.id}&date=2026-07-11')
        self.assertEqual([t['title'] for t in r.data['results']], ['On'])


class ReorderTests(BoardTaskTestCase):
    def test_reorder_updates_accessible_tasks(self):
        t1 = Task.objects.create(board=self.board, title='1', status='todo', order=0)
        self.auth(self.member)
        r = self.client.post('/api/tasks/reorder/', {'updates': [{'id': t1.id, 'status': 'done', 'order': 3}]}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        t1.refresh_from_db()
        self.assertEqual(t1.status, 'done')

    def test_reorder_ignores_inaccessible_tasks(self):
        hidden = Task.objects.create(board=self.other_board, title='H', status='todo', order=0)
        self.auth(self.member)
        r = self.client.post('/api/tasks/reorder/', {'updates': [{'id': hidden.id, 'status': 'done', 'order': 9}]}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        hidden.refresh_from_db()
        self.assertEqual(hidden.status, 'todo')  # untouched


class TagTests(BoardTaskTestCase):
    def test_create_and_list_tags_scoped_to_team(self):
        other_team = Team.objects.create(name='Other', owner=self.outsider)
        Tag.objects.create(team=other_team, name='other-tag')
        self.auth(self.owner)
        r = self.client.post('/api/tags/', {'team': self.team.id, 'name': 'backend'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        r = self.client.get(f'/api/tags/?team={self.team.id}')
        self.assertEqual([t['name'] for t in r.data['results']], ['backend'])

    def test_cannot_create_tag_for_unaccessible_team(self):
        other_team = Team.objects.create(name='Other', owner=self.outsider)
        self.auth(self.owner)
        r = self.client.post('/api/tags/', {'team': other_team.id, 'name': 'x'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
