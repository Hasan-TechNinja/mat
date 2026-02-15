from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from . models import Profile, RegistrationVerifyCode, PasswordResetCode
from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer, UserSerializer
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
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            
            if User.objects.filter(email=email).exists():
                user = User.objects.filter(email=email).first()
                if user.is_active:
                    return Response({'error': "Email is already in use"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    RegistrationVerifyCode.objects.filter(user=user).delete()
            else:
                user = serializer.save()

            code = random.randint(1000, 9999)
            RegistrationVerifyCode.objects.create(user=user, code=code)
            
            try:
                send_mail(
                    'Verification Code',
                    f'Your verification code is: {code}',
                    'noreply@mat.com',
                    [email],
                    fail_silently=False,
                )
            except Exception as e:
                # Fallback for development if email fails
                print(f"Failed to send email: {e}")
                return Response({'message': 'User registered, but failed to send email. Code: ' + str(code)}, status=status.HTTP_201_CREATED)

            return Response({'message': 'A verification code has been sent to your email.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class RegisterVerificationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        gender = request.data.get('gender')
        date_of_birth = request.data.get('date_of_birth')

        if not email or not code:
            return Response({"error": "Email and code are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User does not exist with this email!"}, status=status.HTTP_400_BAD_REQUEST)
        
        checked = RegistrationVerifyCode.objects.filter(user=user, code=code).first()
        if checked:
            if checked.is_expired():
                checked.delete()
                return Response({"error": "Verification code has expired."}, status=status.HTTP_400_BAD_REQUEST)
            
            user.is_active = True
            user.save()
            checked.delete()
            
            # Create Profile
            Profile.objects.get_or_create(
                user=user,
                defaults={
                    'gender': gender if gender else 'Other',
                    'date_of_birth': date_of_birth
                }
            )
            
            return Response({"message": "User successfully activated, now login the account."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid verification code!"}, status=status.HTTP_400_BAD_REQUEST)
        


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            password = serializer.validated_data.get('password')

            user = User.objects.filter(email=email).first()
            if user and user.check_password(password):
                if not user.is_active:
                    return Response({'error': "Account is not activated. Please register first and check your email for verification code."}, status=status.HTTP_400_BAD_REQUEST)
                
                refresh = RefreshToken.for_user(user)
                access_token = refresh.access_token
                
                return Response({
                    'message': "Login Successful",
                    'refresh': str(refresh),
                    'access': str(access_token),
                    'user': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            return Response({'error': "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"error": "Email is required!"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User with this email does not exist!"}, status=status.HTTP_404_NOT_FOUND)
            
        code = random.randint(1000, 9999)

        PasswordResetCode.objects.filter(user=user).delete()
        PasswordResetCode.objects.create(user=user, code=code)
        try:
            send_mail(
                "Password reset code",
                f"Your password reset code is {code}",
                "noreply@mat.com",
                [email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send email: {e}")
            return Response({"message": "Failed to send email, but code generated: " + str(code)}, status=status.HTTP_200_OK)
            
        return Response({"message": "A password reset code has been sent to your email."}, status=status.HTTP_200_OK)



class VerifyPasswordResetCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return Response({"error": "Email and code are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User with this email does not exist!"}, status=status.HTTP_404_NOT_FOUND)
        
        checked = PasswordResetCode.objects.filter(user=user, code=code).first()
        if checked:
            if checked.is_expired():
                checked.delete()
                return Response({"error": "Password reset code has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "Code is valid. You can now reset your password."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid password reset code!"}, status=status.HTTP_400_BAD_REQUEST)
        

class ChangePasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")
        # code = request.data.get("code")

        if not password or not confirm_password:
            return Response({"error": "Password and confirm password are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if password != confirm_password:
            return Response({"error": "Passwords do not match!"}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_authenticated:
            user = request.user
            user.set_password(password)
            user.save()
            PasswordResetCode.objects.filter(user=user).delete()
            return Response({'message': "Password has been changed successfully!"}, status=status.HTTP_200_OK)
        
        # Forgot password flow
        if not email:
            return Response({"error": "Email is required for password reset"}, status=status.HTTP_400_BAD_REQUEST)
            
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User with this email does not exist!"}, status=status.HTTP_404_NOT_FOUND)
            
        reset_code = PasswordResetCode.objects.filter(user=user).first()
        if not reset_code or reset_code.is_expired():
            if reset_code:
                reset_code.delete()
            return Response({"error": "Invalid or expired reset code!"}, status=status.HTTP_400_BAD_REQUEST)
            
        user.set_password(password)
        user.save()
        reset_code.delete()
        return Response({'message': "Password has been reset successfully!"}, status=status.HTTP_200_OK)