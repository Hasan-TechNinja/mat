from django.shortcuts import render

# Create your views here.
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import DeviceTokenSerializer
from .models import DeviceToken
from .serializers import NotificationSerializer
from .models import Notification
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import JSONParser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Count

class DeviceTokenCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Device token registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeviceTokenDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token_str = request.data.get('token')
        if not token_str:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token_obj = DeviceToken.objects.get(user=request.user, token=token_str)
        except DeviceToken.DoesNotExist:
            return Response({"error": "Device token not found"}, status=status.HTTP_404_NOT_FOUND)
        
        token_obj.is_active = False
        token_obj.save()
        return Response({"message": "Device token deactivated successfully"}, status=status.HTTP_200_OK)


class NotificationPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100

class NotificationListView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class NotificationDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def put(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        is_read = request.data.get('is_read')
        if is_read is None:
            return Response({"error": "is_read field is required"}, status=status.HTTP_400_BAD_REQUEST)
        notif.is_read = bool(is_read)
        notif.save()
        return Response(NotificationSerializer(notif).data)

    def delete(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.delete()
        return Response({"message": "Notification deleted"}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unread_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({"unread_count": count})


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def mark_multiple_read(request):
    ids = request.data.get('ids', [])
    if not isinstance(ids, list):
        return Response({"error": "ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)
    Notification.objects.filter(user=request.user, id__in=ids).update(is_read=True)
    return Response({"message": "Marked read"}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Expecting JSON: { "refresh": "<token>", "device_token": "<device_token>" }
        refresh_token = request.data.get('refresh')
        device_token = request.data.get('device_token')

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                # blacklist if app is installed; if not, this will still work but no DB record created
                token.blacklist()
            except Exception:
                # best-effort: ignore blacklist failure
                pass

        if device_token:
            DeviceToken.objects.filter(user=request.user, token=device_token).update(is_active=False)

        return Response({"message": "Logged out and device token unregistered"}, status=status.HTTP_200_OK)
