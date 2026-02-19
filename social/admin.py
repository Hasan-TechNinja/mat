from django.contrib import admin
from .models import Category, Occasion, Post, PostImage, Comment, Wishlist
# Register your models here.

class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'content', 'category', 'occasion', 'target_category', 'created_at', 'total_likes', 'total_comments')
    search_fields = ('content',)
    list_filter = ('category', 'occasion', 'target_category')
admin.site.register(Category)
admin.site.register(Occasion)
admin.site.register(Post, PostAdmin)
admin.site.register(PostImage)
admin.site.register(Comment)
admin.site.register(Wishlist)