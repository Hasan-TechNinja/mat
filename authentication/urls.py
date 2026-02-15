from django.urls import path
from . import views


urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('register/verify/', views.RegisterVerificationView.as_view(), name='register-verify'),
    path('login/', views.LoginView.as_view(), name='login'),
]
