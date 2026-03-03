from rest_framework import serializers
from . models import Post, PostImage, Comment, Wishlist, Category, Occasion
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
    is_saved = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'user', 'content', 'category', 'occasion', 'amazon_link',
            'amazon_product_name', 'amazon_product_image_url',
            'target_category', 'likes', 'comments', 'likes_count',
            'comments_count', 'views', 'created_at', 'profile', 'images',
            'is_saved', 'is_liked', 'status'
        ]

    def get_comments(self, obj):
        # Get related comments and serialize them
        comments = obj.comment.all().order_by('-created_at')
        return CommentSerializer(comments, many=True).data

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Wishlist.objects.filter(post=obj, user=request.user).exists()
        return False

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_status(self, obj):
        return self.context.get('status', None)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.category:
            representation['category'] = {
                'id': instance.category.id,
                'name': instance.category.name
            }
        if instance.occasion:
            representation['occasion'] = {
                'id': instance.occasion.id,
                'name': instance.occasion.name
            }
        return representation




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


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class OccasionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Occasion
        fields = ['id', 'name']