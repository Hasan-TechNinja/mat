from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from ckeditor.fields import RichTextField
from datetime import timedelta

# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    # followers = models.ManyToManyField('self', symmetrical=False, related_name='following')
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    blocked_users = models.ManyToManyField('self', symmetrical=False, related_name='blocked_by', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Kids', 'Kids')])
    is_subscribed = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile of {self.user.username}"
    

class RegistrationVerifyCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Verification code for {self.user.username}"
    
    def is_expired(self):

        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)
    

class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Password reset code for {self.user.username}"
    
    def is_expired(self):
        
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)
    

class PrivacyPolicy(models.Model):
    content = RichTextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Privacy Policy created at {self.created_at}"


class TermsAndConditions(models.Model):
    content = RichTextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Terms and Conditions created at {self.created_at}"


class AccountDeletionRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='deletion_request')
    reason = models.TextField(blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    scheduled_deletion_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    cancelled_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.scheduled_deletion_date:
            self.scheduled_deletion_date = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() >= self.scheduled_deletion_date

    @property
    def days_remaining(self):
        if self.status != 'pending':
            return 0
        remaining = (self.scheduled_deletion_date - timezone.now()).days
        return max(remaining, 0)

    def __str__(self):
        return f"Deletion request for {self.user.email} - {self.status}"