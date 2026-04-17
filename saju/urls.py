from django.urls import path
from .views import DogRegisterView, SajuBasicsView, AIInterpretationView, DailyWalkingLuckView, CompatibilityView

urlpatterns = [
    path('dogs/', DogRegisterView.as_view(), name='dog-register'),
    path('dogs/<int:dog_id>/basics/', SajuBasicsView.as_view(), name='dog-basics'),
    path('dogs/<int:dog_id>/personality/', AIInterpretationView.as_view(), name='dog-personality'),
    path('dogs/<int:dog_id>/daily-luck/', DailyWalkingLuckView.as_view(), name='dog-daily-luck'),
    path('dogs/<int:dog_id>/compatibility/', CompatibilityView.as_view(), name='dog-compatibility'),
]
