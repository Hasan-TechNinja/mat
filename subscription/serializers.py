from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'slug', 'price', 'current_duration_days', 'features']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    is_active = serializers.BooleanField(source='is_active_subscription', read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan', 'status', 'start_date', 'end_date',
            'payment_method', 'transaction_id', 'auto_renew',
            'is_active', 'days_remaining', 'created_at',
        ]


class PurchaseSerializer(serializers.Serializer):
    plan_slug = serializers.SlugField(required=True)
    payment_method = serializers.ChoiceField(
        choices=['stripe', 'google_play', 'apple_iap', 'other'],
        default='other',
    )
    transaction_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class AppPurchaseSerializer(serializers.Serializer):
    plan_slug = serializers.SlugField(required=True)
