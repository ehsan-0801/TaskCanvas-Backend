from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Board, BoardAccess, Team, TeamMembership


class TeamApiTestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'owner@example.com', 'secretpass123')
        self.member = User.objects.create_user('member', 'member@example.com', 'secretpass123')
        self.outsider = User.objects.create_user('out', 'out@example.com', 'secretpass123')

    def auth(self, user):
        self.client.force_authenticate(user=user)


class TeamCrudTests(TeamApiTestCase):
    def test_create_team_makes_caller_owner(self):
        self.auth(self.owner)
        r = self.client.post('/api/teams/', {'name': 'Acme'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        team = Team.objects.get(id=r.data['id'])
        self.assertEqual(team.owner, self.owner)
        self.assertTrue(TeamMembership.objects.filter(team=team, user=self.owner, role='owner').exists())

    def test_list_only_shows_own_or_member_teams(self):
        mine = Team.objects.create(name='Mine', owner=self.owner)
        Team.objects.create(name='Theirs', owner=self.outsider)
        self.auth(self.owner)
        r = self.client.get('/api/teams/')
        names = [t['name'] for t in r.data['results']]
        self.assertEqual(names, ['Mine'])
        self.assertEqual(r.data['results'][0]['role'], 'owner')


class MemberTests(TeamApiTestCase):
    def test_owner_adds_new_user_by_email_password(self):
        team = Team.objects.create(name='Acme', owner=self.owner)
        self.auth(self.owner)
        r = self.client.post(
            f'/api/teams/{team.id}/members/',
            {'email': 'newbie@example.com', 'password': 'brandnew123', 'name': 'New Bie'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='newbie@example.com')
        self.assertTrue(user.check_password('brandnew123'))
        self.assertTrue(TeamMembership.objects.filter(team=team, user=user).exists())

    def test_owner_adds_existing_user_without_password(self):
        team = Team.objects.create(name='Acme', owner=self.owner)
        self.auth(self.owner)
        r = self.client.post(
            f'/api/teams/{team.id}/members/', {'email': 'member@example.com'}, format='json'
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TeamMembership.objects.filter(team=team, user=self.member).exists())

    def test_non_owner_cannot_add_member(self):
        team = Team.objects.create(name='Acme', owner=self.owner)
        TeamMembership.objects.create(team=team, user=self.member, role='member')
        self.auth(self.member)
        r = self.client.post(
            f'/api/teams/{team.id}/members/', {'email': 'x@example.com', 'password': 'pw12345678'}, format='json'
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class BoardTests(TeamApiTestCase):
    def setUp(self):
        super().setUp()
        self.team = Team.objects.create(name='Acme', owner=self.owner)
        TeamMembership.objects.create(team=self.team, user=self.member, role='member')

    def test_owner_creates_multiple_boards(self):
        self.auth(self.owner)
        for name in ['Sprint 1', 'Sprint 2']:
            r = self.client.post('/api/boards/', {'team': self.team.id, 'name': name}, format='json')
            self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Board.objects.filter(team=self.team).count(), 2)

    def test_member_cannot_create_board(self):
        self.auth(self.member)
        r = self.client.post('/api/boards/', {'team': self.team.id, 'name': 'X'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_sees_only_granted_boards(self):
        b1 = Board.objects.create(team=self.team, name='Granted')
        Board.objects.create(team=self.team, name='Hidden')
        BoardAccess.objects.create(board=b1, user=self.member)
        self.auth(self.member)
        r = self.client.get(f'/api/boards/?team={self.team.id}')
        names = [b['name'] for b in r.data['results']]
        self.assertEqual(names, ['Granted'])

    def test_owner_sees_all_team_boards(self):
        Board.objects.create(team=self.team, name='A')
        Board.objects.create(team=self.team, name='B')
        self.auth(self.owner)
        r = self.client.get(f'/api/boards/?team={self.team.id}')
        self.assertEqual(r.data['count'], 2)

    def test_grant_and_revoke_board_access(self):
        board = Board.objects.create(team=self.team, name='Sprint')
        self.auth(self.owner)
        r = self.client.post(f'/api/boards/{board.id}/access/', {'user_id': self.member.id}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(BoardAccess.objects.filter(board=board, user=self.member).exists())
        r = self.client.delete(f'/api/boards/{board.id}/access/{self.member.id}/')
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BoardAccess.objects.filter(board=board, user=self.member).exists())

    def test_cannot_grant_access_to_non_member(self):
        board = Board.objects.create(team=self.team, name='Sprint')
        self.auth(self.owner)
        r = self.client.post(f'/api/boards/{board.id}/access/', {'user_id': self.outsider.id}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
