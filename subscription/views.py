from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import SubscriptionPlan
from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer, PurchaseSerializer
from .services import SubscriptionService
import stripe
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()


class SubscriptionPlanListView(APIView):
    """List all active subscription plans."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PurchaseSubscriptionView(APIView):
    """Purchase or upgrade a subscription."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PurchaseSerializer(data=request.data)
        if serializer.is_valid():
            try:
                subscription = SubscriptionService.purchase_subscription(
                    user=request.user,
                    plan_slug=serializer.validated_data['plan_slug'],
                    payment_method=serializer.validated_data.get('payment_method', 'other'),
                    transaction_id=serializer.validated_data.get('transaction_id'),
                )
                return Response({
                    'message': 'Subscription purchased successfully!',
                    'subscription': UserSubscriptionSerializer(subscription).data,
                }, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MySubscriptionView(APIView):
    """Get the current user's active subscription."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subscription = SubscriptionService.get_active_subscription(request.user)
        if not subscription:
            # Auto-assign free plan
            subscription = SubscriptionService.get_or_create_free_subscription(request.user)

        serializer = UserSubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CancelSubscriptionView(APIView):
    """Cancel the current user's active subscription."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            cancelled_sub = SubscriptionService.cancel_subscription(request.user)
            return Response({
                'message': 'Subscription cancelled successfully.',
                'cancelled_plan': cancelled_sub.plan.name,
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreateStripeCheckoutSessionView(APIView):
    """Create a Stripe checkout session for a subscription plan."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PurchaseSerializer(data=request.data)
        if serializer.is_valid():
            try:
                plan_slug = serializer.validated_data['plan_slug']
                plan = SubscriptionPlan.objects.filter(slug=plan_slug, is_active=True).first()
                if not plan:
                    return Response({'error': 'Subscription plan not found or inactive.'}, status=status.HTTP_404_NOT_FOUND)
                if plan.slug == 'free':
                    return Response({'error': 'Cannot purchase the free plan.'}, status=status.HTTP_400_BAD_REQUEST)

                if not plan.stripe_price_id:
                    return Response({'error': 'Stripe Price ID is not configured for this plan.'}, status=status.HTTP_400_BAD_REQUEST)

                # Create Stripe checkout session
                domain_url = settings.FRONTEND_URL.rstrip('/')

                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price': plan.stripe_price_id,
                        'quantity': 1,
                    }],
                    mode='subscription' if plan.duration_days > 0 else 'payment',
                    customer_email=request.user.email,
                    client_reference_id=str(request.user.id),
                    metadata={
                        'plan_slug': plan.slug,
                    },
                    success_url=domain_url + '/subscription-success/', # Adjust to match frontend route
                    cancel_url=domain_url + '/subscription-cancel/', # Adjust to match frontend route
                )
                return Response({'checkout_url': checkout_session.url}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """Handle Stripe webhooks."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.headers.get('STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        if not endpoint_secret:
            # For testing with self-signed webhooks you might need to drop the signature enforcement
            # But in production you must enforce this
            return Response({'error': 'Webhook secret not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        if not sig_header:
            return Response({'error': 'Missing signature'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Handle the checkout.session.completed event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session.get('client_reference_id')
            plan_slug = session.get('metadata', {}).get('plan_slug')
            stripe_customer_id = session.get('customer')
            stripe_subscription_id = session.get('subscription')

            if user_id and plan_slug:
                try:
                    user = User.objects.get(id=user_id)
                    SubscriptionService.purchase_subscription(
                        user=user,
                        plan_slug=plan_slug,
                        payment_method='stripe',
                        transaction_id=session.get('id'),
                        stripe_customer_id=stripe_customer_id,
                        stripe_subscription_id=stripe_subscription_id
                    )
                except Exception as e:
                    print(f"Error processing subscription for session {session.get('id')}: {e}")
                    pass # Log properly in production

        # Note: You might also want to handle customer.subscription.deleted to cancel automatically
        if event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            stripe_subscription_id = subscription.get('id')
            
            try:
                from .models import UserSubscription
                user_sub = UserSubscription.objects.filter(
                    stripe_subscription_id=stripe_subscription_id, 
                    status='active'
                ).first()
                if user_sub:
                    # Cancel locally since it was deleted on Stripe
                    user_sub.status = 'cancelled'
                    user_sub.auto_renew = False
                    user_sub.save()
                    # Trigger fallback to free plan
                    SubscriptionService.get_or_create_free_subscription(user_sub.user)
                    SubscriptionService._sync_profile(user_sub.user, is_subscribed=False)
            except Exception as e:
                print(f"Error handling subscription cancellation for {stripe_subscription_id}: {e}")

        return Response(status=status.HTTP_200_OK)
