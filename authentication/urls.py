from django.urls import path
from . import views


urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('register/verify/', views.RegisterVerificationView.as_view(), name='register-verify'),
    path('register/resend-otp/', views.ResendRegistrationOTPView.as_view(), name='register-resend-otp'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('social-auth/', views.SocialAuthView.as_view(), name='social-auth'),
    path('password-reset/request/', views.ForgetPasswordView.as_view(), name='password-reset-request'),
    path('password-reset/resend-otp/', views.ResendPasswordResetOTPView.as_view(), name='password-reset-resend-otp'),
    path('password-reset/verify/', views.VerifyPasswordResetCodeView.as_view(), name='password-reset-verify'),
    path('password-reset/change/', views.ChangePasswordView.as_view(), name='password-reset-change'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('change-password/', views.ChangePassword.as_view(), name='change-password'),
    path('follow/<int:user_id>/', views.FollowToggleView.as_view(), name='follow-toggle'),
]
