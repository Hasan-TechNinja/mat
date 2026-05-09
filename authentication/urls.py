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
    path('block/<int:user_id>/', views.BlockToggleView.as_view(), name='block-toggle'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy-policy'),
    path('terms-service/', views.TermsAndConditionsView.as_view(), name='terms-service'),
    path('blocked-users/', views.BlockedUserListView.as_view(), name='blocked-users'),
    path('delete-account/', views.DeleteAccountView.as_view(), name='delete-account'),
    path('cancel-deletion/', views.CancelDeletionView.as_view(), name='cancel-deletion'),
    path('deletion-status/', views.DeletionStatusView.as_view(), name='deletion-status'),
    path('set-password/', views.SetFirstPasswordView.as_view(), name='set-password'),
    path('followers/', views.FollowersListView.as_view(), name='followers'),
    path('following/', views.FollowingListView.as_view(), name='following'),
]
