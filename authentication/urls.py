from django.urls import path
from . import views


urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('register/verify/', views.RegisterVerificationView.as_view(), name='register-verify'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('password-reset/request/', views.ForgetPasswordView.as_view(), name='password-reset-request'),
    path('password-reset/verify/', views.VerifyPasswordResetCodeView.as_view(), name='password-reset-verify'),
    path('password-reset/change/', views.ChangePasswordView.as_view(), name='password-reset-change'),
    path('profile/', views.ProfileView.as_view(), name='profile')
]
