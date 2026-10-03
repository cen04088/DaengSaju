"""
URL configuration for config project.

실제 화면은 앱인토스에 배포되는 frontend/(Granite) 번들이고, 이 서버는 API와 공유 썸네일 이미지만 제공합니다.
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include


def health(request):
    return JsonResponse({'service': 'daengsaju-api', 'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/saju/', include('saju.urls')),
    path('', health, name='health'),
]
