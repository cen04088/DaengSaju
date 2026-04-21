"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
import mimetypes

# Windows 레지스트리 버그로 인해 JS 파일이 text/plain으로 서빙되는 문제 해결
mimetypes.add_type('application/javascript', '.js')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/saju/', include('saju.urls')),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
]
