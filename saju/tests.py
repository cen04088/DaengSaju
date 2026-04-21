from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import Compatibility, CompatibilityArchetype, Dog, SajuBasics, User
from .views import CompatibilityResultView, DogRegisterView


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
