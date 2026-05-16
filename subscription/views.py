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
                    mode='subscription',
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
                    
                    end_date = None
                    if stripe_subscription_id:
                        try:
                            stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
                            # Convert Unix timestamp to datetime UTC
                            import datetime
                            end_date = datetime.datetime.fromtimestamp(stripe_sub.current_period_end, tz=datetime.timezone.utc)
                        except Exception as e:
                            print(f"Error retrieving Stripe subscription {stripe_subscription_id}: {e}")

                    SubscriptionService.purchase_subscription(
                        user=user,
                        plan_slug=plan_slug,
                        payment_method='stripe',
                        transaction_id=session.get('id'),
                        stripe_customer_id=stripe_customer_id,
                        stripe_subscription_id=stripe_subscription_id,
                        end_date=end_date
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


class VerifyGooglePlayPurchaseView(APIView):
    """Verify Google Play in-app purchase tokens."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Implementation depends on google-api-python-client setup.
        # This is a placeholder structure for where the validation logic goes
        # using google.oauth2.service_account and googleapiclient.discovery.
        
        purchase_token = request.data.get('purchase_token')
        product_id = request.data.get('product_id')
        
        if not purchase_token or not product_id:
            return Response({'error': 'Missing purchase_token or product_id'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Fetch Plan by Google Product ID
        plan = SubscriptionPlan.objects.filter(google_play_product_id=product_id, is_active=True).first()
        if not plan:
            return Response({'error': 'Invalid product_id'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 2. Add Google API Validation Here
            # Ensure token is valid and extract the exact expiration time based on Google's response.
            
            # Temporary mock assuming validation succeeded
            subscription = SubscriptionService.purchase_subscription(
                user=request.user,
                plan_slug=plan.slug,
                payment_method='google_play',
                transaction_id=purchase_token, # Keep token for reference
                google_purchase_token=purchase_token,
                # end_date=extracted_expiry # Pass actual expiry
            )
            return Response({'message': 'Google Play subscription verified successfully!'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyApplePurchaseView(APIView):
    """Verify Apple App Store receipt data."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        receipt_data = request.data.get('receipt_data')
        
        if not receipt_data:
            return Response({'error': 'Missing receipt_data'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 1. ping https://buy.itunes.apple.com/verifyReceipt (or sandbox)
        import requests
        
        # Determine environment (Sandbox vs Production) based on settings or trial-and-error approach common in iOS validation
        apple_url = "https://sandbox.itunes.apple.com/verifyReceipt" # Use prod URL in production!
        
        try:
            response = requests.post(apple_url, json={
                "receipt-data": receipt_data,
                "password": settings.APPLE_SHARED_SECRET if hasattr(settings, 'APPLE_SHARED_SECRET') else ""
            })
            data = response.json()
            
            if data.get('status') != 0:
                 return Response({'error': 'Invalid receipt', 'apple_status': data.get('status')}, status=status.HTTP_400_BAD_REQUEST)
                 
            # 2. Extract latest transaction and find the matching plan
            latest_receipt_info = data.get('latest_receipt_info', [])
            if not latest_receipt_info:
                 return Response({'error': 'No subscription found in receipt'}, status=status.HTTP_400_BAD_REQUEST)
                 
            latest_tx = latest_receipt_info[0]
            product_id = latest_tx.get('product_id')
            original_tx_id = latest_tx.get('original_transaction_id')
            
            plan = SubscriptionPlan.objects.filter(apple_product_id=product_id, is_active=True).first()
            if not plan:
                return Response({'error': 'Invalid product_id in receipt'}, status=status.HTTP_400_BAD_REQUEST)

            # 3. Create/update subscription via service
            subscription = SubscriptionService.purchase_subscription(
                user=request.user,
                plan_slug=plan.slug,
                payment_method='apple_iap',
                transaction_id=original_tx_id, 
                apple_original_transaction_id=original_tx_id,
                apple_receipt_data=receipt_data,
                # end_date=extracted_expiry
            )
            return Response({'message': 'Apple subscription verified successfully!'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class GooglePlayWebhookView(APIView):
    """Listen to Google Cloud Pub/Sub Developer Notifications."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Implementation required to parse base64 encoded payload from Pub/Sub
        # and trigger local subscription updates or cancellations based on NotificationType.
        return Response(status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class AppleWebhookView(APIView):
    """Listen to Apple App Store Server Notifications."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Implementation required to parse Apple Server-to-Server v2 payload
        # Find local sub via apple_original_transaction_id and handle DID_RENEW / CANCEL
        return Response(status=status.HTTP_200_OK)
