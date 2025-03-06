from django.urls import path
from apps.image import views

urlpatterns = [
    path('upload', views.UploadImageView.as_view(), name='upload'),
]