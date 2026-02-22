from rest_framework import serializers
from .models import DeviceToken
from .models import Notification

class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ['token', 'platform', 'osVersion', 'deviceName']

    def create(self, validated_data):
        user = self.context['request'].user
        token = validated_data.get('token')

        # Update or create device token based on user + token
        device_token, created = DeviceToken.objects.update_or_create(
            user=user,
            token=token,
            defaults={
                'platform': validated_data.get('platform', 'unknown'),
                'osVersion': validated_data.get('osVersion'),
                'deviceName': validated_data.get('deviceName'),
                'is_active': True
            }
        )
        return device_token


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'body', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']
