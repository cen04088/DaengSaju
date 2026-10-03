from django.urls import path
from .views import (
    AIInterpretationView,
    AttendanceView,
    CompatibilityResultView,
    DailyWalkingLuckView,
    DogRegisterView,
    DogShareView,
    FriendCompatibilityView,
    MyDogsView,
    SajuBasicsView,
    SharedCardView,
)

urlpatterns = [
    path('dogs/', DogRegisterView.as_view(), name='dog-register'),
    path('me/dogs/', MyDogsView.as_view(), name='my-dogs'),
    path('dogs/<int:dog_id>/basics/', SajuBasicsView.as_view(), name='dog-basics'),
    path('dogs/<int:dog_id>/personality/', AIInterpretationView.as_view(), name='dog-personality'),
    path('dogs/<int:dog_id>/daily-luck/', DailyWalkingLuckView.as_view(), name='dog-daily-luck'),
    path('dogs/<int:dog_id>/compatibility/', CompatibilityResultView.as_view(), name='dog-compatibility'),
    path('dogs/<int:dog_id>/friend-compatibility/', FriendCompatibilityView.as_view(), name='dog-friend-compatibility'),
    path('dogs/<int:dog_id>/share/', DogShareView.as_view(), name='dog-share'),
    path('share/<slug:token>/', SharedCardView.as_view(), name='shared-card'),
    path('attendance/', AttendanceView.as_view(), name='attendance'),
]
