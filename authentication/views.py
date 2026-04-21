from urllib import request
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from . models import PrivacyPolicy, Profile, RegistrationVerifyCode, PasswordResetCode, TermsAndConditions, AccountDeletionRequest
from .serializers import PrivacyPolicySerializer, RegisterSerializer, LoginSerializer, ProfileSerializer, UserSerializer, SocialAuthSerializer, TermsAndConditionsSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions
from django.utils import timezone
import random
import string
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta

# Create your views here.

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        gender = request.data.get('gender')
        date_of_birth = request.data.get('date_of_birth')

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

            # Create Profile
            Profile.objects.get_or_create(
                user=user,
                defaults={
                    'gender': gender if gender else 'Other',
                    'date_of_birth': date_of_birth
                }
            )

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
            

            
            return Response({"message": "User successfully activated, now login the account."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid verification code!"}, status=status.HTTP_400_BAD_REQUEST)
        

class ResendRegistrationOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User with this email does not exist!"}, status=status.HTTP_404_NOT_FOUND)
        
        if user.is_active:
            return Response({"error": "User is already verified and active."}, status=status.HTTP_400_BAD_REQUEST)

        code = random.randint(1000, 9999)
        RegistrationVerifyCode.objects.filter(user=user).delete()
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
            print(f"Failed to send email: {e}")
            return Response({'message': 'Failed to send email, but code generated: ' + str(code)}, status=status.HTTP_201_CREATED)

        return Response({'message': 'A new verification code has been sent to your email.'}, status=status.HTTP_200_OK)


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

                access_token['first_name'] = user.first_name
                access_token['last_name'] = user.last_name
                access_token['email'] = user.email
                access_token['role'] = "admin" if user.is_superuser else "user"

                user_data = {
                    'user_id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'role': "admin" if user.is_superuser else "user",
                }
                
                # Cancel any pending account deletion request if user logs in
                deletion_request = AccountDeletionRequest.objects.filter(user=user, status='pending').first()
                if deletion_request:
                    deletion_request.status = 'cancelled'
                    deletion_request.cancelled_at = timezone.now()
                    deletion_request.save()
                    
                return Response({
                    'message': "Login Successful",
                    'refresh': str(refresh),
                    'access': str(access_token),
                    'user': user_data,
                    'deletion_request_cancelled': deletion_request is not None
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


class ResendPasswordResetOTPView(APIView):
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
                f"Your new password reset code is {code}",
                "noreply@mat.com",
                [email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send email: {e}")
            return Response({"message": "Failed to send email, but code generated: " + str(code)}, status=status.HTTP_200_OK)
            
        return Response({"message": "A new password reset code has been sent to your email."}, status=status.HTTP_200_OK)


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
    


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = request.query_params.get('id')
        if user_id:
            profile = get_object_or_404(Profile, user_id=user_id)
        else:
            profile = get_object_or_404(Profile, user=request.user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        profile = get_object_or_404(Profile, user=request.user)
        user = profile.user
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name = request.data.get('last_name', user.last_name)
        user.email = request.data.get('email', user.email)
        user.save()
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ChangePassword(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not old_password or not new_password or not confirm_password:
            return Response({"error": "All fields are required!"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(old_password):
            return Response({"error": "Old password is incorrect!"}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({"error": "New password and confirm password do not match!"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"message": "Password has been changed successfully!"}, status=status.HTTP_200_OK)


class FollowToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        try:
            target_profile = Profile.objects.get(user_id=user_id)
        except Profile.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        my_profile = get_object_or_404(Profile, user=request.user)

        if target_profile.user == request.user:
            return Response({"error": "You cannot follow yourself"}, status=status.HTTP_400_BAD_REQUEST)

        if my_profile.following.filter(id=target_profile.id).exists():
            my_profile.following.remove(target_profile)
            return Response({"message": "Unfollowed successfully"}, status=status.HTTP_200_OK)
        else:
            my_profile.following.add(target_profile)

            # Send notification to the followed user
            from notification.fcm_utils import send_push_notification
            send_push_notification(
                user=target_profile.user,
                title="New Follower",
                body=f"{request.user.username} started following you.",
                data={"type": "follow", "user_id": str(request.user.id)}
            )

            return Response({"message": "Followed successfully"}, status=status.HTTP_201_CREATED)


class BlockToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
            target_profile = target_user.profile
        except (User.DoesNotExist, Profile.DoesNotExist):
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        my_profile = get_object_or_404(Profile, user=request.user)

        if target_user == request.user:
            return Response({"error": "You cannot block yourself"}, status=status.HTTP_400_BAD_REQUEST)

        if my_profile.blocked_users.filter(id=target_profile.id).exists():
            my_profile.blocked_users.remove(target_profile)
            return Response({"message": "User unblocked successfully"}, status=status.HTTP_200_OK)
        else:
            my_profile.blocked_users.add(target_profile)
            
            # Mutual unfollow when blocking
            my_profile.following.remove(target_profile)
            target_profile.following.remove(my_profile)
            
            return Response({"message": "User blocked successfully"}, status=status.HTTP_201_CREATED)

class BlockedUserListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        my_profile = get_object_or_404(Profile, user=request.user)
        blocked_users = my_profile.blocked_users.all()
        serializer = ProfileSerializer(blocked_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SocialAuthView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            first_name = serializer.validated_data.get('first_name', '')
            last_name = serializer.validated_data.get('last_name', '')

            user = User.objects.filter(email=email).first()

            if not user:
                base_username = email
                username = base_username
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{random.randint(1000, 9999)}"

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )
                user.set_unusable_password()
                user.is_active = True
                user.save()
                
                Profile.objects.create(
                    user=user,
                    gender='Other',
                )

            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # access_token['first_name'] = user.first_name
            # access_token['last_name'] = user.last_name
            # access_token['email'] = user.email
            # access_token['role'] = "admin" if user.is_superuser else "user"

            profile = Profile.objects.filter(user=user).first()
            if profile:
                profile_serializer = ProfileSerializer(profile, context={'request': request})
                user_data = profile_serializer.data
                user_data['user_id'] = user.id
                user_data['role'] = "admin" if user.is_superuser else "user"
            else:
                user_data = {
                    'user_id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'role': "admin" if user.is_superuser else "user",
                }

            # Cancel any pending account deletion request if user logs in via social auth
            deletion_request = AccountDeletionRequest.objects.filter(user=user, status='pending').first()
            if deletion_request:
                deletion_request.status = 'cancelled'
                deletion_request.cancelled_at = timezone.now()
                deletion_request.save()

            return Response({
                'message': "Social Authentication Successful",
                'refresh': str(refresh),
                'access': str(access_token),
                'user': user_data,
                'deletion_request_cancelled': deletion_request is not None
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class PrivacyPolicyView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        policy = PrivacyPolicy.objects.order_by('-created_at').first()
        if not policy:
            return Response({"error": "Privacy policy not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PrivacyPolicySerializer(policy)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TermsAndConditionsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        terms = TermsAndConditions.objects.order_by('-created_at').first()
        if not terms:
            return Response({"error": "Terms and conditions not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TermsAndConditionsSerializer(terms)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        email = request.data.get('email', '')
        password = request.data.get('password', '')
        reason = request.data.get('reason', '')

        # Validate that email and password are provided
        if not email or not password:
            return Response(
                {"error": "Email and password are required to delete your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify the email matches the authenticated user
        if email.lower().strip() != user.email.lower().strip():
            return Response(
                {"error": "The email address does not match your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify the password is correct
        if not user.check_password(password):
            return Response(
                {"error": "Incorrect password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Check subscription
        active_subscription = user.subscriptions.filter(status='active').first()
        if active_subscription and active_subscription.plan.slug != 'free' and user.profile.is_subscribed:
            return Response(
                {"error": "You cannot delete your account because you have an active subscription. Please cancel your subscription from the billing provider first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if there's already a pending deletion request
        existing = AccountDeletionRequest.objects.filter(user=user, status='pending').first()
        if existing:
            return Response({
                "message": "You already have a pending deletion request.",
                "scheduled_deletion_date": existing.scheduled_deletion_date,
                "days_remaining": existing.days_remaining,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Remove any existing (cancelled/completed) deletion request to start fresh
        AccountDeletionRequest.objects.filter(user=user).delete()

        # Create a new deletion request (30 days from now)
        deletion_request = AccountDeletionRequest.objects.create(
            user=user,
            reason=reason,
            scheduled_deletion_date=timezone.now() + timedelta(days=31),
        )

        return Response({
            "message": "Account deletion request submitted. Your account will be permanently deleted after 30 days. If you log in before then, the request will be cancelled.",
            "scheduled_deletion_date": deletion_request.scheduled_deletion_date,
            "days_remaining": deletion_request.days_remaining,
        }, status=status.HTTP_200_OK)

    def delete(self, request):
        """Also support DELETE method for backward compatibility."""
        return self.post(request)


class CancelDeletionView(APIView):
    """Explicitly cancel a pending account deletion request."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            deletion_request = AccountDeletionRequest.objects.get(user=user, status='pending')
            deletion_request.status = 'cancelled'
            deletion_request.cancelled_at = timezone.now()
            deletion_request.save()
            return Response({"message": "Account deletion request has been cancelled."}, status=status.HTTP_200_OK)
        except AccountDeletionRequest.DoesNotExist:
            return Response({"error": "No pending deletion request found."}, status=status.HTTP_404_NOT_FOUND)


class DeletionStatusView(APIView):
    """Check the status of account deletion request."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        deletion_request = AccountDeletionRequest.objects.filter(user=user).order_by('-requested_at').first()
        if not deletion_request:
            return Response({"has_pending_deletion": False}, status=status.HTTP_200_OK)

        return Response({
            "has_pending_deletion": deletion_request.status == 'pending',
            "status": deletion_request.status,
            "requested_at": deletion_request.requested_at,
            "scheduled_deletion_date": deletion_request.scheduled_deletion_date,
            "days_remaining": deletion_request.days_remaining,
            "cancelled_at": deletion_request.cancelled_at,
        }, status=status.HTTP_200_OK)