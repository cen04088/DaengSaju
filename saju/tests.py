from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import Compatibility, CompatibilityArchetype, Dog, SajuBasics, User
from .views import AttendanceView, CompatibilityResultView, DogAnalysisBundleView, DogRegisterView


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


class DogAnalysisBundleViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = DogAnalysisBundleView.as_view()
        self.user = User.objects.create_user(
            username='bundle-owner',
            password='test-pass',
            social_id='bundle-owner',
            nickname='Owner',
        )
        self.dog = Dog.objects.create(
            user=self.user,
            name='Mung',
            birth_date='2020-01-01',
            gender='MALE',
        )
        self.saju = SajuBasics.objects.create(
            dog=self.dog,
            year_pillar='AA',
            month_pillar='BB',
            day_pillar='CC',
            hour_pillar='DD',
            main_element='목',
            element_distribution={'목': 100},
            relationship_type='비겁',
            secondary_element='목',
        )

    @patch('saju.views.get_or_create_ai_interpretation_for_dog')
    @patch('saju.views.get_or_create_daily_luck_for_dog')
    def test_bundle_returns_combined_payload(
        self,
        mock_daily_luck,
        mock_interpretation,
    ):
        mock_interpretation.return_value = (
            {
                'personality_summary': '요약',
                'personality_keywords': ['키워드'],
                'vitality_analysis': '활력',
                'social_analysis': '사회성',
                'treat_luck': '간식운',
                'care_tips': '케어팁',
                'updated_at': '2026-04-22T00:00:00Z',
            },
            False,
        )
        mock_daily_luck.return_value = (
            {
                'date': '2026-04-22',
                'luck_score': 88,
                'message': '산책운 최고',
                'lucky_color': '하늘색',
                'lucky_direction': '동쪽',
            },
            False,
        )

        request = self.factory.get(f'/api/saju/dogs/{self.dog.id}/analysis/')
        response = self.view(request, dog_id=self.dog.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['basics']['main_element'], '목')
        self.assertEqual(response.data['personality']['personality_summary'], '요약')
        self.assertEqual(response.data['daily_luck']['luck_score'], 88)


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

    @patch('saju.views.add_hanja_to_terms', side_effect=lambda text: text)
    @patch('saju.views.get_relationship_type', return_value='owner-rel-1')
    @patch('saju.views.get_saju_for_dog', return_value={'main_element': 'OWNER1'})
    def test_compatibility_replaces_spaced_placeholders_in_response(
        self,
        _mock_get_saju_for_dog,
        _mock_get_relationship_type,
        _mock_add_hanja,
    ):
        archetype = CompatibilityArchetype.objects.get(
            dog_element='DOG',
            relationship_type='owner-rel-1',
            version='B',
        )
        archetype.title = '[\uac15\uc544\uc9c0 \uc774\ub984]\uacfc [\ubcf4\ud638\uc790 \uc774\ub984]\uc758 \uad81\ud569'
        archetype.description = '[\ubcf4\ud638\uc790 \uc774\ub984]\ub2d8\uacfc [\uac15\uc544\uc9c0 \uc774\ub984]\uc758 \uc778\uc5f0'
        archetype.advice = '[\ubcf4\ud638\uc790 \uc774\ub984]\ub2d8\ub2d8\uc740 [\uac15\uc544\uc9c0 \uc774\ub984]\uc640 \uc790\uc8fc \ub180\uc544\uc8fc\uc138\uc694.'
        archetype.save(update_fields=['title', 'description', 'advice'])

        request = self.factory.post(
            f'/api/saju/dogs/{self.dog.id}/compatibility/',
            {'owner_birth_date': '1990-01-01'},
            format='json',
        )
        response = self.view(request, dog_id=self.dog.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Mung\uacfc \ubcf4\ud638\uc790\ub2d8\uc758 \uad81\ud569')
        self.assertEqual(response.data['description'], '\ubcf4\ud638\uc790\ub2d8\uacfc Mung\uc758 \uc778\uc5f0')
        self.assertEqual(response.data['advice'], '\ubcf4\ud638\uc790\ub2d8\uc740 Mung\uc640 \uc790\uc8fc \ub180\uc544\uc8fc\uc138\uc694.')

    @patch('saju.views.add_hanja_to_terms', side_effect=lambda text: text)
    @patch('saju.views.get_relationship_type', return_value='owner-rel-1')
    @patch('saju.views.get_saju_for_dog', return_value={'main_element': 'OWNER1'})
    def test_compatibility_replaces_leftover_owner_placeholder_variants(
        self,
        _mock_get_saju_for_dog,
        _mock_get_relationship_type,
        _mock_add_hanja,
    ):
        archetype = CompatibilityArchetype.objects.get(
            dog_element='DOG',
            relationship_type='owner-rel-1',
            version='B',
        )
        archetype.title = '[강아지 이름]과 [보호자 이름]의 궁합'
        archetype.description = '[보호자 이름]님과 [강아지 이름]의 인연'
        archetype.advice = '[보호자 이름]님님은 [강아지 이름]와 자주 놀아주세요.'
        archetype.save(update_fields=['title', 'description', 'advice'])

        request = self.factory.post(
            f'/api/saju/dogs/{self.dog.id}/compatibility/',
            {'owner_birth_date': '1990-01-01'},
            format='json',
        )
        response = self.view(request, dog_id=self.dog.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Mung과 보호자님의 궁합')
        self.assertEqual(response.data['description'], '보호자님과 Mung의 인연')
        self.assertEqual(response.data['advice'], '보호자님은 Mung와 자주 놀아주세요.')
