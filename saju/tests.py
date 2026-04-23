from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import Compatibility, CompatibilityArchetype, Dog, SajuBasics, User
from .views import (
    AttendanceView,
    CompatibilityResultView,
    DogRegisterView,
    normalize_owner_honorific_text,
)


class DogRegisterViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = DogRegisterView.as_view()

    def test_reuses_existing_dog_for_identical_payload(self):
        payload = {
            'social_id': 'owner-key',
            'nickname': 'Owner',
            'dog': {
                'name': 'Mung',
                'birth_date': '2020-01-01',
                'birth_time': None,
                'is_lunar': False,
                'gender': 'MALE',
                'is_estimated_birth': False,
            },
        }

        first = self.view(self.factory.post('/api/saju/dogs/', payload, format='json'))
        second = self.view(self.factory.post('/api/saju/dogs/', payload, format='json'))

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['dog_id'], second.data['dog_id'])
        self.assertEqual(Dog.objects.count(), 1)

    def test_accepts_toss_user_key_header(self):
        payload = {
            'nickname': 'Owner',
            'dog': {
                'name': 'Mung',
                'birth_date': '2020-01-01',
                'birth_time': None,
                'is_lunar': False,
                'gender': 'MALE',
                'is_estimated_birth': False,
            },
        }

        request = self.factory.post('/api/saju/dogs/', payload, format='json', HTTP_X_TOSS_USER_KEY='header-key')
        response = self.view(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get().social_id, 'header-key')


class AttendanceViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AttendanceView.as_view()

    def test_reads_social_id_from_toss_header(self):
        request = self.factory.get('/api/saju/attendance/', format='json', HTTP_X_TOSS_USER_KEY='header-key')
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get().social_id, 'header-key')

    def test_first_attendance_claims_day_one_milestone(self):
        request = self.factory.post('/api/saju/attendance/', {'social_id': 'first-day-key'}, format='json')
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['stamped'])
        self.assertEqual(response.data['streak_count'], 1)
        self.assertEqual(response.data['new_milestone'], 1)


class CompatibilityViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = CompatibilityResultView.as_view()
        self.user = User.objects.create_user(
            username='owner-key',
            password='test-pass',
            social_id='owner-key',
            nickname='Owner',
        )
        self.dog = Dog.objects.create(
            user=self.user,
            name='Mung',
            birth_date='2020-01-01',
            gender='MALE',
        )
        SajuBasics.objects.create(
            dog=self.dog,
            year_pillar='AA',
            month_pillar='BB',
            day_pillar='CC',
            hour_pillar='DD',
            main_element='DOG',
            element_distribution={'DOG': 100},
            relationship_type='rel-dog',
            secondary_element='DOG',
        )
        CompatibilityArchetype.objects.create(
            dog_element='DOG',
            relationship_type='owner-rel-1',
            version='B',
            score=81,
            title='Title 1',
            description='Desc 1',
            advice='Advice 1',
        )
        CompatibilityArchetype.objects.create(
            dog_element='DOG',
            relationship_type='owner-rel-2',
            version='B',
            score=93,
            title='Title 2',
            description='Desc 2',
            advice='Advice 2',
        )

    @patch('saju.views.smart_replace', side_effect=lambda text, dog_name, owner_name=None: text)
    @patch('saju.views.add_hanja_to_terms', side_effect=lambda text: text)
    @patch('saju.views.get_relationship_type')
    @patch('saju.views.get_saju_for_dog')
    def test_compatibility_uses_current_owner_input_even_when_cache_exists(
        self,
        mock_get_saju_for_dog,
        mock_get_relationship_type,
        _mock_add_hanja,
        _mock_replace,
    ):
        mock_get_saju_for_dog.side_effect = [
            {'main_element': 'OWNER1'},
            {'main_element': 'OWNER2'},
        ]
        mock_get_relationship_type.side_effect = ['owner-rel-1', 'owner-rel-2']

        Compatibility.objects.create(
            dog=self.dog,
            user=self.user,
            score=10,
            title='Old title',
            description='DOG|OWNER0|stale|Old desc',
        )

        first_request = self.factory.post(
            f'/api/saju/dogs/{self.dog.id}/compatibility/',
            {'owner_birth_date': '1990-01-01'},
            format='json',
        )
        first = self.view(first_request, dog_id=self.dog.id)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data['owner_element'], 'OWNER1')
        self.assertEqual(first.data['score'], 81)

        second_request = self.factory.post(
            f'/api/saju/dogs/{self.dog.id}/compatibility/',
            {'owner_birth_date': '1992-02-02'},
            format='json',
        )
        second = self.view(second_request, dog_id=self.dog.id)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data['owner_element'], 'OWNER2')
        self.assertEqual(second.data['score'], 93)

        cached = Compatibility.objects.get(dog=self.dog, user=self.user)
        self.assertTrue(cached.description.startswith('DOG|OWNER2|owner-rel-2|'))


class HonorificNormalizationTests(TestCase):
    def test_collapses_repeated_owner_honorific_patterns(self):
        owner_name = '보호자님'
        text = '보호자님님 보호자님이님 보호자님은님 보호자님이님이'

        normalized = normalize_owner_honorific_text(text, owner_name)

        self.assertEqual(normalized, '보호자님 보호자님이 보호자님은 보호자님이')

    def test_normalizes_stacked_owner_particles(self):
        owner_name = '보호자님'
        text = '보호자님이의 마음과 보호자님이께 드리는 인사, 보호자님가에게 전하는 소식'

        normalized = normalize_owner_honorific_text(text, owner_name)

        self.assertEqual(normalized, '보호자님의 마음과 보호자님께 드리는 인사, 보호자님에게 전하는 소식')
