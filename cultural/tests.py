from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Event, Team

User = get_user_model()

class TeamTests(TestCase):
    def setUp(self):
        # create users
        self.leader = User.objects.create_user(moodleID=1001, password='pass1234')
        self.member = User.objects.create_user(moodleID=1002, password='pass1234')
        # events
        self.event = Event.objects.create(name='Valorant', slug='valorant')
        self.other_event = Event.objects.create(name='Chess', slug='chess')

    def test_create_team_success(self):
        self.client.force_login(self.leader)
        url = reverse('cultural-team-create')
        data = {'event_slug': 'valorant', 'name': 'Team A', 'member_moodle_ids': [1002], 'secondary_contact_number': '0123456789'}
        resp = self.client.post(url, data, content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Team.objects.count(), 1)
        team = Team.objects.first()
        self.assertEqual(team.leader, self.leader)
        self.assertIn(self.member, team.members.all())

    def test_member_cannot_be_in_two_teams_same_event(self):
        # create first team with member
        t = Team.objects.create(event=self.event, name='T1', leader=self.leader)
        t.members.add(self.member)
        # another leader tries to create team with same member
        other = User.objects.create_user(moodleID=2001, password='pass')
        self.client.force_login(other)
        url = reverse('cultural-team-create')
        data = {'event_slug': 'valorant', 'name': 'Team B', 'member_moodle_ids': [1002]}
        resp = self.client.post(url, data, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('member_moodle_ids', resp.data)

    def test_member_with_registration_cannot_join_team(self):
        # member registers individually first
        Registration.objects.create(student=self.member, event=self.event, year='FE')
        # leader tries to create team including that member
        self.client.force_login(self.leader)
        url = reverse('cultural-team-create')
        data = {'event_slug': 'valorant', 'name': 'Team C', 'member_moodle_ids': [1002]}
        resp = self.client.post(url, data, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('member_moodle_ids', resp.data)

    def test_cannot_create_team_for_non_team_event(self):
        self.client.force_login(self.leader)
        url = reverse('cultural-team-create')
        data = {'event_slug': 'chess', 'name': 'Team Chess', 'member_moodle_ids': []}
        resp = self.client.post(url, data, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('event_slug', resp.data)

    def test_cannot_register_if_in_team(self):
        # leader creates a team
        t = Team.objects.create(event=self.event, name='T1', leader=self.leader)
        t.members.add(self.leader)
        # leader tries to register individually
        self.client.force_login(self.leader)
        url = reverse('cultural-register')
        data = {'event_slug': 'valorant'}
        resp = self.client.post(url, data, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.data)

