from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.DeviceTokenCreateView.as_view(), name='device-token-register'),
    path('deactivate/', views.DeviceTokenDeleteView.as_view(), name='device-token-deactivate'),
    path('', views.NotificationListView.as_view(), name='notifications-list'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('unread-count/', views.unread_count, name='notifications-unread-count'),
    path('mark-read/', views.mark_multiple_read, name='notifications-mark-read'),
    path('logout/', views.LogoutView.as_view(), name='notifications-logout'),
]
