from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    # followers = models.ManyToManyField('self', symmetrical=False, related_name='following')
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])

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