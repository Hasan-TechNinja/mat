from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price', 'stripe_price_id', 'duration_days', 'is_active']
    list_filter = ['is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'payment_method', 'start_date', 'end_date', 'auto_renew']
    list_filter = ['status', 'payment_method', 'plan']
    search_fields = ['user__username', 'user__email', 'transaction_id']
    raw_id_fields = ['user']
