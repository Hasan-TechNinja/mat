from django.urls import path
from . import views

urlpatterns = [
    path('plans/', views.SubscriptionPlanListView.as_view(), name='subscription-plans'),
    path('purchase/', views.PurchaseSubscriptionView.as_view(), name='subscription-purchase'),
    path('my-subscription/', views.MySubscriptionView.as_view(), name='my-subscription'),
    path('cancel/', views.CancelSubscriptionView.as_view(), name='subscription-cancel'),
    path('create-checkout-session/', views.CreateStripeCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('webhook/', views.StripeWebhookView.as_view(), name='stripe-webhook'),
    path('verify/google/', views.VerifyGooglePlayPurchaseView.as_view(), name='verify-google'),
    path('verify/apple/', views.VerifyApplePurchaseView.as_view(), name='verify-apple'),
    path('webhook/google/', views.GooglePlayWebhookView.as_view(), name='google-webhook'),
    path('webhook/apple/', views.AppleWebhookView.as_view(), name='apple-webhook'),
]
