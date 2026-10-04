"""
URL configuration for config project.

실제 화면은 앱인토스에 배포되는 frontend/(Granite) 번들이고, 이 서버는 API와 공유 썸네일 이미지만 제공합니다.
"""
import os

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include

# Railway가 GitHub 배포 때 넣어 주는 커밋 값: 새 버전이 실제로 떴는지 확인하는 데 씀
DEPLOYED_COMMIT = os.environ.get('RAILWAY_GIT_COMMIT_SHA', '')[:7]


def health(request):
    return JsonResponse({'service': 'daengsaju-api', 'status': 'ok', 'commit': DEPLOYED_COMMIT})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/saju/', include('saju.urls')),
    path('', health, name='health'),
]
