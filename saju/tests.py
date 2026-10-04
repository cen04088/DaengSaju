import io
import os
import re
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from .models import (
    AIInterpretation,
    Attendance,
    Compatibility,
    CompatibilityArchetype,
    DailyLuckArchetype,
    DailyWalkingLuck,
    Dog,
    SajuBasics,
    User,
)
from .compatibility_copy import COMPATIBILITY_COPY
from .services.manseryeok import get_saju_for_dog, smart_replace
from .services.tone import normalize_copy, to_haeyo
from .services.profiles import (
    BRANCHES,
    ILJU_NICKNAMES,
    STEMS,
    attach_josa,
    get_day_pillar_profile,
    get_zodiac_relation,
)
from .views import (
    ARCHETYPE_VERSIONS,
    AttendanceView,
    CompatibilityResultView,
    DogRegisterView,
    build_daily_luck,
    compute_attendance_streak,
    normalize_compatibility_owner_text,
    normalize_owner_honorific_text,
)

OWNER_KEY = 'owner-key'


def dog_payload(**overrides):
    dog = {
        'name': 'Mung',
        'birth_date': '2020-01-01',
        'birth_time': None,
        'is_lunar': False,
        'gender': 'MALE',
        'is_estimated_birth': False,
    }
    dog.update(overrides)
    return {'nickname': 'Owner', 'dog': dog}


def make_user(social_id=OWNER_KEY):
    return User.objects.create_user(username=social_id, password='test-pass', social_id=social_id, nickname='Owner')


class DogRegisterViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = DogRegisterView.as_view()

    def post(self, payload, key=OWNER_KEY):
        headers = {'HTTP_X_TOSS_USER_KEY': key} if key else {}
        return self.view(self.factory.post('/api/saju/dogs/', payload, format='json', **headers))

    def test_reuses_existing_dog_for_identical_payload(self):
        first = self.post(dog_payload())
        second = self.post(dog_payload())

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['dog_id'], second.data['dog_id'])
        self.assertFalse(second.data['updated'])
        self.assertEqual(Dog.objects.count(), 1)

    def test_accepts_toss_user_key_header(self):
        response = self.post(dog_payload(), key='header-key')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get().social_id, 'header-key')

    def test_ignores_social_id_in_body_without_header(self):
        payload = dog_payload()
        payload['social_id'] = 'spoofed-key'

        response = self.post(payload, key=None)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.exists())

    def test_same_name_with_new_birth_info_updates_dog_and_clears_results(self):
        first = self.post(dog_payload())
        dog = Dog.objects.get(id=first.data['dog_id'])
        SajuBasics.objects.create(
            dog=dog, year_pillar='己亥', month_pillar='丙子', day_pillar='甲子', hour_pillar=None,
            main_element='목', element_distribution={'목': 100}, relationship_type='비겁', secondary_element='목',
        )

        second = self.post(dog_payload(birth_date='2021-03-03'))

        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data['updated'])
        self.assertEqual(second.data['dog_id'], dog.id)
        dog.refresh_from_db()
        self.assertEqual(dog.birth_date, date(2021, 3, 3))
        self.assertFalse(SajuBasics.objects.filter(dog=dog).exists())

    def test_rejects_leap_month_that_does_not_exist(self):
        response = self.post(dog_payload(birth_date='2021-04-01', is_lunar=True, is_leap_month=True))

        self.assertEqual(response.status_code, 400)
        self.assertIn('음력', response.data['error'])
        self.assertFalse(Dog.objects.exists())

    def test_rejects_future_birth_date(self):
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()

        response = self.post(dog_payload(birth_date=tomorrow))

        self.assertEqual(response.status_code, 400)

    def test_leap_month_flag_is_ignored_for_solar_dates(self):
        response = self.post(dog_payload(is_leap_month=True))

        self.assertEqual(response.status_code, 201)
        self.assertFalse(Dog.objects.get().is_leap_month)


class LunarBirthdayTests(TestCase):
    def test_lunar_birthday_is_converted_before_calculating(self):
        lunar = get_saju_for_dog(date(2020, 4, 1), is_lunar=True)
        solar = get_saju_for_dog(date(2020, 4, 23))

        self.assertEqual(lunar['day_pillar'], solar['day_pillar'])
        self.assertEqual(lunar['month_pillar'], solar['month_pillar'])

    def test_leap_month_uses_second_occurrence(self):
        leap = get_saju_for_dog(date(2020, 4, 1), is_lunar=True, is_leap_month=True)
        solar = get_saju_for_dog(date(2020, 5, 23))

        self.assertEqual(leap['day_pillar'], solar['day_pillar'])

    def test_basics_endpoint_uses_lunar_flag(self):
        user = make_user()
        dog = Dog.objects.create(user=user, name='Dal', birth_date='2020-04-01', is_lunar=True, gender='FEMALE')
        client = APIClient()

        response = client.get(f'/api/saju/dogs/{dog.id}/basics/', HTTP_X_TOSS_USER_KEY=OWNER_KEY)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['day_pillar'], get_saju_for_dog(date(2020, 4, 23))['day_pillar'])


class OwnershipTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = make_user()
        self.dog = Dog.objects.create(user=self.owner, name='Mung', birth_date='2020-01-01', gender='MALE')

    def test_requires_user_key_header(self):
        response = self.client.get(f'/api/saju/dogs/{self.dog.id}/basics/')

        self.assertEqual(response.status_code, 403)

    def test_other_users_cannot_read_my_dog(self):
        response = self.client.get(f'/api/saju/dogs/{self.dog.id}/basics/', HTTP_X_TOSS_USER_KEY='someone-else')

        self.assertEqual(response.status_code, 404)
        self.assertFalse(SajuBasics.objects.exists())

    def test_my_dogs_lists_only_my_dogs_newest_first(self):
        newer = Dog.objects.create(user=self.owner, name='Bori', birth_date='2021-05-05', gender='FEMALE')
        other = make_user('other-key')
        Dog.objects.create(user=other, name='Stranger', birth_date='2019-01-01', gender='MALE')

        response = self.client.get('/api/saju/me/dogs/', HTTP_X_TOSS_USER_KEY=OWNER_KEY)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([d['id'] for d in response.data['dogs']], [newer.id, self.dog.id])
        self.assertNotIn('share_token', response.data['dogs'][0])


class DailyLuckTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.dog = Dog.objects.create(user=self.user, name='Mung', birth_date='2020-01-01', gender='MALE')
        for relationship in ['비겁', '인성', '식상', '재성', '관성']:
            for version in ['A', 'B', 'C']:
                DailyLuckArchetype.objects.create(
                    dog_element='목', relationship_type=relationship, version=version,
                    message=f'{relationship}-{version} [강아지이름]이와 산책', lucky_color='초록', lucky_direction='동쪽',
                )

    def test_message_follows_the_days_element(self):
        with patch('saju.views.get_daily_pillar', return_value={'pillar': '甲子', 'element': '목'}):
            same_element = build_daily_luck(self.dog, '목', date(2026, 10, 4))
        with patch('saju.views.get_daily_pillar', return_value={'pillar': '庚午', 'element': '금'}):
            metal_day = build_daily_luck(self.dog, '목', date(2026, 10, 4))

        self.assertTrue(same_element['message'].startswith('비겁-'))
        self.assertTrue(metal_day['message'].startswith('관성-'))  # 금극목: 그날 기운이 강아지를 극함

    def test_version_rotates_by_date(self):
        with patch('saju.views.get_daily_pillar', return_value={'pillar': '甲子', 'element': '목'}):
            versions = {build_daily_luck(self.dog, '목', date(2026, 10, 1) + timedelta(days=i))['message'][3] for i in range(3)}

        self.assertEqual(versions, {'A', 'B', 'C'})

    def test_score_is_stable_for_the_same_day(self):
        with patch('saju.views.get_daily_pillar', return_value={'pillar': '甲子', 'element': '목'}):
            first = build_daily_luck(self.dog, '목', date(2026, 10, 4))
            second = build_daily_luck(self.dog, '목', date(2026, 10, 4))

        self.assertEqual(first['luck_score'], second['luck_score'])

    def test_endpoint_returns_today_context_and_caches(self):
        SajuBasics.objects.create(
            dog=self.dog, year_pillar='己亥', month_pillar='丙子', day_pillar='甲子', hour_pillar=None,
            main_element='목', element_distribution={'목': 100}, relationship_type='비겁', secondary_element='목',
        )
        url = f'/api/saju/dogs/{self.dog.id}/daily-luck/'

        first = self.client.get(url, HTTP_X_TOSS_USER_KEY=OWNER_KEY)
        second = self.client.get(url, HTTP_X_TOSS_USER_KEY=OWNER_KEY)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['message'], second.data['message'])
        self.assertIn(first.data['today_element'], ['목', '화', '토', '금', '수'])
        self.assertEqual(len(first.data['today_pillar']), 2)
        self.assertEqual(DailyWalkingLuck.objects.count(), 1)


class AttendanceViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AttendanceView.as_view()

    def test_reads_social_id_from_toss_header(self):
        request = self.factory.get('/api/saju/attendance/', format='json', HTTP_X_TOSS_USER_KEY='header-key')
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get().social_id, 'header-key')

    def test_rejects_social_id_in_body(self):
        request = self.factory.post('/api/saju/attendance/', {'social_id': 'spoofed-key'}, format='json')
        response = self.view(request)

        self.assertEqual(response.status_code, 403)

    def test_first_attendance_claims_day_one_milestone(self):
        request = self.factory.post('/api/saju/attendance/', {}, format='json', HTTP_X_TOSS_USER_KEY='first-day-key')
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['stamped'])
        self.assertEqual(response.data['streak_count'], 1)
        self.assertEqual(response.data['total_days'], 1)
        self.assertEqual(response.data['streak_days'], 1)
        self.assertEqual(response.data['new_milestone'], 1)

    def test_second_stamp_on_same_day_is_ignored(self):
        request = lambda: self.factory.post('/api/saju/attendance/', {}, format='json', HTTP_X_TOSS_USER_KEY='key')
        self.view(request())
        second = self.view(request())

        self.assertFalse(second.data['stamped'])
        self.assertIsNone(second.data['new_milestone'])
        self.assertEqual(second.data['total_days'], 1)

    def test_streak_continues_across_months(self):
        user = make_user()
        Attendance.objects.create(user=user, year=2026, month=9, attended_days=[28, 29, 30])
        Attendance.objects.create(user=user, year=2026, month=10, attended_days=[1, 2])

        self.assertEqual(compute_attendance_streak(user, date(2026, 10, 2)), 5)
        # 오늘 아직 출석 전이면 어제까지의 연속 기록을 보여줌
        self.assertEqual(compute_attendance_streak(user, date(2026, 10, 3)), 5)
        self.assertEqual(compute_attendance_streak(user, date(2026, 10, 4)), 0)


class CompatibilityViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = CompatibilityResultView.as_view()
        self.user = make_user()
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

    def post(self, payload):
        request = self.factory.post(
            f'/api/saju/dogs/{self.dog.id}/compatibility/', payload, format='json', HTTP_X_TOSS_USER_KEY=OWNER_KEY,
        )
        return self.view(request, dog_id=self.dog.id)

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

        first = self.post({'owner_birth_date': '1990-01-01'})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data['owner_element'], 'OWNER1')
        self.assertEqual(first.data['score'], 81)

        second = self.post({'owner_birth_date': '1992-02-02'})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data['owner_element'], 'OWNER2')
        self.assertEqual(second.data['score'], 93)

        cached = Compatibility.objects.get(dog=self.dog, user=self.user)
        self.assertTrue(cached.description.startswith('DOG|OWNER2|owner-rel-2|'))

    @patch('saju.views.add_hanja_to_terms', side_effect=lambda text: text)
    @patch('saju.views.get_relationship_type', return_value='owner-rel-1')
    @patch('saju.views.get_saju_for_dog', return_value={'main_element': 'OWNER1'})
    def test_compatibility_hides_owner_name_and_uses_generic_honorific(
        self,
        _mock_get_saju_for_dog,
        _mock_get_relationship_type,
        _mock_add_hanja,
    ):
        CompatibilityArchetype.objects.filter(
            dog_element='DOG',
            relationship_type='owner-rel-1',
            version='B',
        ).update(
            title='[강아지이름]과 [보호자이름]의 궁합',
            description='[보호자 이름]와 [강아지이름]는 잘 맞고 민수님이의 마음도 편안해져요.',
            advice='민수와 [강아지이름]가 함께할 때는 [보호자이름]를 바라보는 시간을 늘려주세요.',
        )

        response = self.post({'owner_birth_date': '1990-01-01', 'owner_name': '민수님'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('보호자님', response.data['title'])
        self.assertIn('보호자님과', response.data['description'])
        self.assertIn('보호자님을', response.data['advice'])
        self.assertNotIn('민수', response.data['description'])
        self.assertNotIn('[보호자', response.data['advice'])

    @patch('saju.views.get_relationship_type', return_value='owner-rel-1')
    @patch('saju.views.get_saju_for_dog', return_value={'main_element': 'OWNER1', 'year_pillar': '甲丑'})
    def test_zodiac_harmony_adjusts_score(self, _mock_get_saju_for_dog, _mock_get_relationship_type):
        SajuBasics.objects.filter(dog=self.dog).update(year_pillar='庚子')  # 쥐띠 강아지 × 소띠 보호자 = 육합

        response = self.post({'owner_birth_date': '1985-03-03'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['base_score'], 81)
        self.assertEqual(response.data['score'], 88)
        self.assertEqual(response.data['zodiac']['type'], '육합(六合)')
        self.assertEqual(response.data['zodiac']['label'], '찰떡 띠 궁합(육합)')

    @patch('saju.views.add_hanja_to_terms', side_effect=lambda text: text)
    @patch('saju.views.get_relationship_type', return_value='owner-rel-1')
    @patch('saju.views.get_saju_for_dog', return_value={'main_element': 'OWNER1'})
    def test_bare_owner_placeholder_does_not_get_subject_particle(self, *_mocks):
        CompatibilityArchetype.objects.filter(dog_element='DOG', relationship_type='owner-rel-1').update(
            title='[강아지이름]의 든든한 리더, [보호자이름]',
        )

        response = self.post({'owner_birth_date': '1990-01-01'})

        self.assertEqual(response.data['title'], 'Mung의 든든한 리더, 보호자님')

    def test_requires_owner_birth_date(self):
        response = self.post({})

        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.data['error'])


class CompatibilityCopyTests(TestCase):
    def test_copy_uses_haeyo_tone_and_consistent_owner_address(self):
        for key, template in COMPATIBILITY_COPY.items():
            for field in ('description', 'advice'):
                text = template[field]
                sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]
                formal = [s for s in sentences if re.search(r'니다[.!]?$', s)]
                self.assertEqual(formal, [], f'{key} {field}: 습니다체 문장')
                self.assertIsNone(re.search(r'보호자(?!님)', text), f"{key} {field}: '보호자님' 대신 '보호자'")

    def test_refresh_command_syncs_all_archetypes(self):
        call_command('refresh_compatibility_copy', stdout=io.StringIO())

        self.assertEqual(CompatibilityArchetype.objects.count(), 50)
        sample = CompatibilityArchetype.objects.get(dog_element='목', relationship_type='관성', version='A')
        self.assertIn('목(木) 기운을 타고났어요', sample.description)
        self.assertNotIn('[보호자', sample.title)


class FriendCompatibilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.dog = Dog.objects.create(user=self.user, name='초코', birth_date='2020-01-01', gender='MALE')
        self.url = f'/api/saju/dogs/{self.dog.id}/friend-compatibility/'

    def post(self, payload):
        return self.client.post(self.url, payload, format='json', HTTP_X_TOSS_USER_KEY=OWNER_KEY)

    def test_returns_deterministic_result(self):
        payload = {'friend_name': '보리', 'friend_birth_date': '2021-06-15'}

        first = self.post(payload)
        second = self.post(payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data, second.data)
        self.assertTrue(60 <= first.data['score'] <= 99)
        self.assertEqual(first.data['friend_name'], '보리')
        self.assertTrue(first.data['friend_profile']['nickname'])
        self.assertNotIn('{', first.data['description'])

    def test_validates_friend_input(self):
        response = self.post({'friend_name': '', 'friend_birth_date': '2021-06-15'})

        self.assertEqual(response.status_code, 400)


class ShareCardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.dog = Dog.objects.create(user=self.user, name='Mung', birth_date='2020-01-01', gender='MALE')

    def test_share_token_is_stable_and_public_card_hides_birth_info(self):
        url = f'/api/saju/dogs/{self.dog.id}/share/'
        first = self.client.post(url, HTTP_X_TOSS_USER_KEY=OWNER_KEY)
        second = self.client.post(url, HTTP_X_TOSS_USER_KEY=OWNER_KEY)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data['token'], second.data['token'])

        card = self.client.get(f"/api/saju/share/{first.data['token']}/")
        self.assertEqual(card.status_code, 200)
        self.assertEqual(card.data['dog_name'], 'Mung')
        self.assertTrue(card.data['profile']['nickname'])
        for hidden in ('birth_date', 'birth_time', 'year_pillar', 'day_pillar', 'dog_id'):
            self.assertNotIn(hidden, card.data)

    def test_other_users_cannot_create_share_token(self):
        response = self.client.post(f'/api/saju/dogs/{self.dog.id}/share/', HTTP_X_TOSS_USER_KEY='other')

        self.assertEqual(response.status_code, 404)

    def test_unknown_token_returns_404(self):
        response = self.client.get('/api/saju/share/not-a-token/')

        self.assertEqual(response.status_code, 404)


class PersonalityProfileTests(TestCase):
    def test_personality_includes_day_pillar_profile(self):
        from .models import ArchetypeSaju

        user = make_user()
        dog = Dog.objects.create(user=user, name='Mung', birth_date='2020-01-01', gender='MALE')
        saju = get_saju_for_dog(date(2020, 1, 1))
        ArchetypeSaju.objects.create(
            primary_element=saju['main_element'], relationship_type=saju['relationship_type'], version='A',
            personality_summary='[강아지이름]는 멋져요', personality_keywords=['#멋짐'], vitality_analysis='v',
            social_analysis='s', treat_luck='t', care_tips='c',
        )

        response = APIClient().get(f'/api/saju/dogs/{dog.id}/personality/', HTTP_X_TOSS_USER_KEY=OWNER_KEY)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['day_pillar_profile']['pillar_hanja'], saju['day_pillar'])
        self.assertTrue(response.data['zodiac']['label'].endswith('띠'))
        self.assertEqual(AIInterpretation.objects.count(), 1)


class ProfileContentTests(TestCase):
    def test_every_sexagenary_day_has_a_nickname(self):
        stems = list(STEMS.values())
        branches = list(BRANCHES.values())
        pillars = {stems[i % 10]['ko'] + branches[i % 12]['ko'] for i in range(60)}

        self.assertEqual(pillars, set(ILJU_NICKNAMES))

    def test_day_pillar_profile(self):
        profile = get_day_pillar_profile('甲戌')

        self.assertEqual(profile['pillar'], '갑술')
        self.assertEqual(profile['element'], '목')
        self.assertEqual(len(profile['keywords']), 2)
        self.assertIsNone(get_day_pillar_profile('알수'))

    def test_zodiac_relations(self):
        self.assertEqual(get_zodiac_relation('자', '축')['type'], '육합(六合)')
        self.assertEqual(get_zodiac_relation('인', '오')['type'], '삼합(三合)')
        self.assertEqual(get_zodiac_relation('자', '오')['type'], '충(沖)')
        self.assertEqual(get_zodiac_relation('자', '자')['type'], '같은 띠')
        self.assertEqual(get_zodiac_relation('자', '묘')['type'], '평(平)')

    def test_attach_josa(self):
        self.assertEqual(attach_josa('초코', '와/과'), '초코와')
        self.assertEqual(attach_josa('은빛', '와/과'), '은빛과')
        self.assertEqual(attach_josa('보리', '이/가'), '보리가')


class SecurityConfigTests(TestCase):
    def test_only_public_assets_are_collected_as_static_files(self):
        self.assertIsNotNone(finders.find(os.path.join('assets', 'fire_dog.png')))
        for slug in ('wood', 'fire', 'earth', 'metal', 'water'):
            self.assertIsNotNone(finders.find(os.path.join('assets', f'og_{slug}.jpg')), f'공유 카드 og_{slug}.jpg')
        self.assertIsNone(finders.find('config/settings.py'))
        self.assertIsNone(finders.find('full_saju_data.json'))

    def test_cors_allows_only_toss_origins(self):
        client = APIClient()
        preflight = {'HTTP_ACCESS_CONTROL_REQUEST_METHOD': 'GET', 'HTTP_ACCESS_CONTROL_REQUEST_HEADERS': 'x-toss-user-key'}

        for origin in (
            'https://daengsaju.apps.tossmini.com',
            'https://daengsaju.private-apps.tossmini.com',
            'https://daengsaju.web.tossmini.com',
            'https://daengsaju.private-web.tossmini.com',
        ):
            allowed = client.options('/api/saju/attendance/', HTTP_ORIGIN=origin, **preflight)
            self.assertEqual(allowed['Access-Control-Allow-Origin'], origin)

        for origin in ('https://evil.example', 'https://other.apps.tossmini.com'):
            blocked = client.options('/api/saju/attendance/', HTTP_ORIGIN=origin, **preflight)
            self.assertNotIn('Access-Control-Allow-Origin', blocked)

    def test_root_is_a_health_check(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')


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

    def test_normalizes_compatibility_owner_placeholders(self):
        text = '[보호자 이름]와 [강아지이름]의 궁합, [보호자이름]를 향한 마음, 보호자님가 전하는 말'

        normalized = normalize_compatibility_owner_text(text, '민수님')

        self.assertEqual(
            normalized,
            '보호자님과 [강아지이름]의 궁합, 보호자님을 향한 마음, 보호자님이 전하는 말',
        )

    def test_normalizes_stacked_compatibility_owner_particles(self):
        text = (
            '보호자님이은 웃고, 보호자님이와 걷고, 보호자님가를 바라보고, '
            '보호자님가의 마음을 읽고, 보호자님은은 다정해요.'
        )

        normalized = normalize_compatibility_owner_text(text, '민수님')

        self.assertEqual(
            normalized,
            '보호자님은 웃고, 보호자님과 걷고, 보호자님을 바라보고, '
            '보호자님의 마음을 읽고, 보호자님은 다정해요.',
        )


class ToneNormalizationTests(TestCase):
    def test_formal_endings_become_haeyo(self):
        cases = {
            '탐험을 즐기는 경향이 있답니다.': '탐험을 즐기는 경향이 있어요.',
            '먹을 복이 많은 아이랍니다!': '먹을 복이 많은 아이예요!',
            '사랑스러운 댕댕이랍니다!': '사랑스러운 댕댕이예요!',
            '기운이 가득한 날이랍니다!': '기운이 가득한 날이에요!',
            '마음을 키워줄 것입니다.': '마음을 키워줄 거예요.',
            '일관된 환경이 중요합니다!': '일관된 환경이 중요해요!',
            '큰 도움이 됩니다.': '큰 도움이 돼요.',
            '미식가 타입에 가깝습니다!': '미식가 타입에 가까워요!',
            '피아식별이 빠르답니다.': '피아식별이 빨라요.',
            '시늉을 할지도 모른답니다.': '시늉을 할지도 몰라요.',
            '열정적으로 달려든답니다.': '열정적으로 달려들어요.',
            '영리함을 보입니다.': '영리함을 보여요.',
            '보호자님을 돕는답니다.': '보호자님을 도와요.',
            '그냥 간식이 아니랍니다.': '그냥 간식이 아니에요.',
            '사랑 그 자체이십니다.': '사랑 그 자체이세요.',
            '추억 많이 만드시길 바랍니다!': '추억 많이 만드시길 바라요!',
            '포근한 기운이 감도는 하루입니다.': '포근한 기운이 감도는 하루예요.',
        }
        for before, after in cases.items():
            with self.subTest(before=before):
                self.assertEqual(to_haeyo(before), after)

    def test_keeps_plain_forms_and_is_idempotent(self):
        self.assertEqual(to_haeyo('다정하게 대하지만, 아니다 싶은 상대에게는'), '다정하게 대하지만, 아니다 싶은 상대에게는')
        once = normalize_copy('경향이 깊답니다 . 정말 특별하답니다!')
        self.assertEqual(once, '경향이 깊어요. 정말 특별해요!')
        self.assertEqual(normalize_copy(once), once)


class SmartReplaceParticleTests(TestCase):
    def test_nickname_i_before_other_particles(self):
        cases = [
            ('[강아지이름]이의 꼬리', '은빛이의 꼬리', '단비의 꼬리'),
            ('[강아지이름]이에게 산책은', '은빛이에게 산책은', '단비에게 산책은'),
            ('[강아지이름]이은 영리해요', '은빛이는 영리해요', '단비는 영리해요'),
            ('[강아지이름]이지만', '은빛이지만', '단비지만'),
            ('[강아지이름]아, 오늘도', '은빛아, 오늘도', '단비야, 오늘도'),
            ("'[강아지이름]'이와 꼭 닮은", "'은빛'이와 꼭 닮은", "'단비'와 꼭 닮은"),
            ('[강아지이름]이 신났어요', '은빛이 신났어요', '단비가 신났어요'),
        ]
        for text, with_batchim, without_batchim in cases:
            with self.subTest(text=text):
                self.assertEqual(smart_replace(text, '은빛'), with_batchim)
                self.assertEqual(smart_replace(text, '단비'), without_batchim)


class NormalizeCopyToneCommandTests(TestCase):
    def setUp(self):
        from .models import ArchetypeSaju

        self.dog = Dog.objects.create(user=make_user(), name='단비', birth_date='2020-01-01', gender='FEMALE')
        SajuBasics.objects.create(
            dog=self.dog, year_pillar='己亥', month_pillar='丙子', day_pillar='甲子', hour_pillar=None,
            main_element='목', element_distribution={'목': 100}, relationship_type='비겁', secondary_element='목',
        )
        self.archetype = ArchetypeSaju.objects.create(
            primary_element='목', relationship_type='비겁', version=ARCHETYPE_VERSIONS[self.dog.id % 3],
            personality_summary='[강아지이름]는 자유로운 영혼이랍니다!', personality_keywords=['#자유'],
            vitality_analysis='[강아지이름]이의 에너지는 정말 대단하답니다.', social_analysis='친구를 좋아한답니다.',
            treat_luck='간식운이 좋습니다.', care_tips='산책이 중요합니다.',
        )
        for relationship in ['비겁', '인성', '식상', '재성', '관성']:
            for version in ARCHETYPE_VERSIONS:
                DailyLuckArchetype.objects.create(
                    dog_element='목', relationship_type=relationship, version=version,
                    message='오늘은 [강아지이름]이에게 정말 좋은 날입니다.', lucky_color='초록', lucky_direction='동쪽',
                )
        # 예전 코드가 저장해 둔 강아지별 문구: 합니다체 + 받침 없는 이름의 조사 오류('단비가의')
        self.interpretation = AIInterpretation.objects.create(
            dog=self.dog, personality_summary='단비는 자유로운 영혼이랍니다!', personality_keywords=['#자유'],
            vitality_analysis='단비가의 에너지는 정말 대단하답니다.', social_analysis='친구를 좋아한답니다.',
            treat_luck='간식운이 좋습니다.', care_tips='예전에 따로 써 둔 팁이에요. 간식을 아껴 먹는답니다.',
        )
        self.luck = DailyWalkingLuck.objects.create(
            dog=self.dog, date=timezone.localdate(), luck_score=80, lucky_color='초록', lucky_direction='동쪽',
            message='오늘은 단비가에게 정말 좋은 날입니다.',
        )

    def test_rewrites_archetypes_and_saved_copy(self):
        call_command('normalize_copy_tone', stdout=io.StringIO())

        self.archetype.refresh_from_db()
        self.interpretation.refresh_from_db()
        self.luck.refresh_from_db()
        self.assertEqual(self.archetype.personality_summary, '[강아지이름]는 자유로운 영혼이에요!')
        # 같은 원본에서 나온 글은 새로 만들어 어미와 이름 조사가 함께 고쳐짐
        self.assertEqual(self.interpretation.vitality_analysis, '단비의 에너지는 정말 대단해요.')
        self.assertEqual(self.luck.message, '오늘은 단비에게 정말 좋은 날이에요.')
        # 원본과 다른 글은 내용을 지키고 어미만 정리
        self.assertEqual(self.interpretation.care_tips, '예전에 따로 써 둔 팁이에요. 간식을 아껴 먹어요.')

    def test_second_run_changes_nothing(self):
        call_command('normalize_copy_tone', stdout=io.StringIO())
        out = io.StringIO()
        call_command('normalize_copy_tone', stdout=out)

        self.assertIn('이미 정리돼 있어요', out.getvalue())
