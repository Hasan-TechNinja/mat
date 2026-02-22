from django.contrib import admin
from .models import DeviceToken, Notification


class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'platform', 'deviceName', 'is_active', 'created_at')
    list_filter = ('platform', 'is_active')
    search_fields = ('user__username', 'token', 'deviceName')

admin.site.register(DeviceToken, DeviceTokenAdmin)


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('user__username', 'title', 'body')

admin.site.register(Notification, NotificationAdmin)
