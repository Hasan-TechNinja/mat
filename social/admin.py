from django.contrib import admin
from .models import Category, Occasion, Post, PostImage, Comment, Wishlist, ReportPost
# Register your models here.

class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 1

class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'content', 'category', 'occasion', 'target_category', 'created_at', 'total_likes', 'total_comments', 'approval')
    search_fields = ('content',)
    list_filter = ('category', 'occasion', 'target_category', 'approval')
    inlines = [PostImageInline]
    actions = ['approve_posts', 'unapprove_posts']

    @admin.action(description="Approve selected posts")
    def approve_posts(self, request, queryset):
        updated = queryset.update(approval=True)
        self.message_user(request, f"{updated} posts were successfully approved.")

    @admin.action(description="Unapprove selected posts")
    def unapprove_posts(self, request, queryset):
        updated = queryset.update(approval=False)
        self.message_user(request, f"{updated} posts were successfully unapproved.")

admin.site.register(Post, PostAdmin)

class CommentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'post', 'user', 'content', 'created_at'
    )
admin.site.register(Comment, CommentAdmin)

class OccasionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    list_filter = ('name',)
admin.site.register(Occasion, OccasionAdmin)


class PostImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'image')
admin.site.register(PostImage, PostImageAdmin)

class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'created_at')
    search_fields = ('user', 'post')
    list_filter = ('user', 'post')
admin.site.register(Wishlist, WishlistAdmin)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    list_filter = ('name',)
admin.site.register(Category, CategoryAdmin)


class ReportPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'reason', 'created_at')
    search_fields = ('post', 'user', 'reason')
    list_filter = ('reason',)
admin.site.register(ReportPost, ReportPostAdmin)