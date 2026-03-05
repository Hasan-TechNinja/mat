from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)  # e.g. "Free", "Pro"
    slug = models.SlugField(unique=True)    # e.g. "free", "pro"
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    stripe_price_id = models.CharField(max_length=255, null=True, blank=True, help_text="Stripe Price ID (e.g., price_1N...) for this plan")
    google_play_product_id = models.CharField(max_length=255, null=True, blank=True, help_text="Google Play Product ID for this plan")
    apple_product_id = models.CharField(max_length=255, null=True, blank=True, help_text="Apple App Store Product ID for this plan")
    duration_days = models.IntegerField(default=30)  # 30 = monthly
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f"{self.name} (${self.price}/month)"


class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('pending', 'Pending'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('free', 'Free'),
        ('stripe', 'Stripe'),
        ('google_play', 'Google Play'),
        ('apple_iap', 'Apple IAP'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscribers')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='free')
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, null=True, blank=True)
    google_purchase_token = models.CharField(max_length=1000, null=True, blank=True)
    apple_original_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    apple_receipt_data = models.TextField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"

    @property
    def is_active_subscription(self):
        """Check if subscription is currently active and not expired."""
        if self.status != 'active':
            return False
        if self.end_date and timezone.now() > self.end_date:
            return False
        return True

    @property
    def days_remaining(self):
        """Calculate days remaining in the subscription."""
        if not self.end_date:
            return None  # Free plan, no expiry
        remaining = (self.end_date - timezone.now()).days
        return max(0, remaining)
