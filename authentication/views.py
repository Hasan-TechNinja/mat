from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from . models import Profile, RegistrationVerifyCode
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions
from django.utils import timezone
import random
import string
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken

# Create your views here.

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        password = request.data.get('password')
        confirm_password = request.data.get('confirm_password')
        gender = request.data.get('gender')
        date_of_birth = request.data.get('date_of_birth')

        if not email or not first_name or not last_name or not password:
            return Response({'error': 'Email, first name, last name and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if password != confirm_password:
           return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            if User.objects.filter(email=email).first().is_active:
                return Response({'error': "Email is already in use"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                code = random.randint(1000, 9999)
                user = User.objects.filter(email=email).first()
                RegistrationVerifyCode.objects.filter(user=user).delete()
                RegistrationVerifyCode.objects.create(user=user, code=code)
                send_mail(
                    'Verification Code',
                    'Your verification code is: ' + RegistrationVerifyCode.objects.filter(user=User.objects.filter(email=email).first()).first().code,
                    'noreply@mat.com',
                    [email],
                    fail_silently=False,
                )
                return Response({'message': 'A verification code has been sent to your email.'}, status=status.HTTP_200_OK)
            
        user = User.objects.create_user(username=email, email=email, first_name=first_name, last_name=last_name, password=password, is_active=False)
        code = random.randint(1000, 9999)
        RegistrationVerifyCode.objects.create(user=user, code=code)
        send_mail(
            'Verification Code',
            'Your verification code is: ' + RegistrationVerifyCode.objects.filter(user=user).first().code,
            'noreply@mat.com',
            [email],
            fail_silently=False,
        )
        return Response({'message': 'User registered successfully. Please check your email for verification code.'}, status=status.HTTP_201_CREATED)
    


class RegisterVerificationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')

        user = User.objects.get(email = email)
        if not user:
            return Response("User does not exist with this email!", status=status.HTTP_400_BAD_REQUEST)
        checked = RegistrationVerifyCode.objects.filter(user=user, code = code)
        if checked:
            user.is_active = True
            user.save()
            checked.delete()
            return Response({"message": "User successfully activated, now login the account."})
        else:
            return Response({"error": "Invalid verification code!"}, status=status.HTTP_400_BAD_REQUEST)
        


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = User.objects.filter(email=email).first()
        if user and user.check_password(password):
            if not user.is_active:
                return Response({'error': "Account is not activated. Please register first and check your email for verification code."}, status=status.HTTP_400_BAD_REQUEST)
            
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({'message': "Login Successful",
                             'refresh': str(refresh),
                             'access': str(access_token)})

            # return Response({'message': 'Login Successful'}, status=status.HTTP_200_OK)
