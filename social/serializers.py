from rest_framework import serializers
from . models import Post, PostImage, Comment, Wishlist
from authentication.models import Profile
from authentication.serializers import UserSerializer, ProfileSerializer


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'image']


class PostSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    likes = UserSerializer(many=True, read_only=True)  # Full user info instead of IDs
    comments = serializers.SerializerMethodField()     # Custom nested data
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    profile = serializers.ImageField(source = 'user.profile.image', read_only=True)
    images = PostImageSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'user', 'content', 'category', 'occasion', 'amazon_link',
            'target_category', 'likes', 'comments', 'likes_count',
            'comments_count', 'created_at', 'profile', 'images'
        ]

    def get_comments(self, obj):
        # Get related comments and serialize them
        comments = obj.comment.all().order_by('-created_at')
        return CommentSerializer(comments, many=True).data



class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'user', 'content', 'created_at']


class WishlistSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    post = PostSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'post', 'created_at']