from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

class Occasion(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

TARGET_CATEGORIES = [
    ('Men', 'Men'),
    ('Women', 'Women'),
    ('Kids', 'Kids'),
]

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
    occasion = models.ForeignKey(Occasion, on_delete=models.SET_NULL, null=True, related_name='posts')
    amazon_link = models.URLField(blank=True, null=True)
    target_category = models.CharField(max_length=20, choices=TARGET_CATEGORIES)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    comments = models.ManyToManyField(User, through='Comment', related_name='commented_posts', blank=True)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.content[:50]
    
    def total_likes(self):
        return self.likes.count()

    def total_comments(self):
        return self.comments.count()
    
    
class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='post_images/')

    def __str__(self):
        return f"Image for post {self.post.id}"
    
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comment')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_user')
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on post {self.post.id}"
    

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} wishlisted post {self.post.id}"