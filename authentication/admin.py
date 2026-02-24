from django.contrib import admin
from .models import Profile, RegistrationVerifyCode
# Register your models here.

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'image', 'phone', 'created_at', 'date_of_birth', 'gender', 'is_subscribed') 
admin.site.register(Profile, ProfileAdmin)

# class RegistrationVerifyCodeAdmin(admin.ModelAdmin):
#     list_display = ('user', 'code', 'created_at')
# admin.site.register(RegistrationVerifyCode)


admin.site.site_header = "Gift Guru Admin Portal"
admin.site.site_title = "Gift Guru Admin Portal"
admin.site.index_title = "Welcome to Gift Guru Admin Portal" 
admin.site.enable_nav_sidebar = True