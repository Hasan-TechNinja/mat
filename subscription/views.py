from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import SubscriptionPlan
from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer, PurchaseSerializer
from .services import SubscriptionService


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
