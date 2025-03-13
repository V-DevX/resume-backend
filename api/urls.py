# api/urls.py

from django.urls import path
from .views import UploadResumeView

urlpatterns = [
    path('upload/', UploadResumeView.as_view(), name='upload_resume'),
]
