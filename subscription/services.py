from django.utils import timezone
from datetime import timedelta
from .models import SubscriptionPlan, UserSubscription


class SubscriptionService:
    """Centralized business logic for subscription management."""

    @staticmethod
    def get_or_create_free_subscription(user):
        """Ensure user has at least a free subscription."""
        active_sub = UserSubscription.objects.filter(
            user=user, status='active'
        ).select_related('plan').first()

        if active_sub:
            return active_sub

        free_plan = SubscriptionPlan.objects.filter(slug='free').first()
        if not free_plan:
            # Auto-create the free plan if it doesn't exist
            free_plan = SubscriptionPlan.objects.create(
                name='Free',
                slug='free',
                price=0.00,
                duration_days=0,  # 0 = no expiry
                features=[
                    'Affiliate links generated using our affiliate ID',
                    'Add unlimited Amazon product links',
                    'No account configuration required',
                    'Basic support',
                ],
                is_active=True,
            )

        subscription = UserSubscription.objects.create(
            user=user,
            plan=free_plan,
            status='active',
            payment_method='free',
            start_date=timezone.now(),
            end_date=None,  # Free plan never expires
        )
        return subscription

    @staticmethod
    def purchase_subscription(user, plan_slug, payment_method='other', transaction_id=None):
        """
        Purchase or upgrade a subscription.
        - Cancels existing active subscription (if any).
        - Creates a new active subscription for the requested plan.
        - Updates Profile.is_subscribed accordingly.
        """
        plan = SubscriptionPlan.objects.filter(slug=plan_slug, is_active=True).first()
        if not plan:
            raise ValueError("Subscription plan not found or is inactive.")

        if plan.slug == 'free':
            raise ValueError("Cannot purchase the free plan. It is assigned automatically.")

        # Cancel any existing active subscription
        UserSubscription.objects.filter(user=user, status='active').update(
            status='cancelled',
            updated_at=timezone.now(),
        )

        # Create the new subscription
        start = timezone.now()
        end = start + timedelta(days=plan.duration_days) if plan.duration_days > 0 else None

        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            status='active',
            start_date=start,
            end_date=end,
            payment_method=payment_method,
            transaction_id=transaction_id,
            auto_renew=True,
        )

        # Sync Profile.is_subscribed
        SubscriptionService._sync_profile(user, is_subscribed=True)

        return subscription

    @staticmethod
    def cancel_subscription(user):
        """
        Cancel the user's active subscription.
        Falls back to free plan.
        """
        active_sub = UserSubscription.objects.filter(
            user=user, status='active'
        ).select_related('plan').first()

        if not active_sub:
            raise ValueError("No active subscription found.")

        if active_sub.plan.slug == 'free':
            raise ValueError("Cannot cancel the free plan.")

        active_sub.status = 'cancelled'
        active_sub.auto_renew = False
        active_sub.save()

        # Create a free subscription as fallback
        SubscriptionService.get_or_create_free_subscription(user)

        # Sync Profile.is_subscribed
        SubscriptionService._sync_profile(user, is_subscribed=False)

        return active_sub

    @staticmethod
    def get_active_subscription(user):
        """Return the user's current active subscription or None."""
        return UserSubscription.objects.filter(
            user=user, status='active'
        ).select_related('plan').first()

    @staticmethod
    def check_and_expire_subscriptions():
        """
        Batch job: expire subscriptions past their end_date.
        Can be called via a management command or celery task.
        """
        now = timezone.now()
        expired_subs = UserSubscription.objects.filter(
            status='active',
            end_date__isnull=False,
            end_date__lt=now,
        )

        for sub in expired_subs:
            sub.status = 'expired'
            sub.save()

            # Fall back to free plan
            SubscriptionService.get_or_create_free_subscription(sub.user)
            SubscriptionService._sync_profile(sub.user, is_subscribed=False)

        return expired_subs.count()

    @staticmethod
    def _sync_profile(user, is_subscribed):
        """Update the Profile.is_subscribed field."""
        try:
            profile = user.profile
            profile.is_subscribed = is_subscribed
            profile.save(update_fields=['is_subscribed'])
        except Exception:
            pass  # Profile may not exist yet
