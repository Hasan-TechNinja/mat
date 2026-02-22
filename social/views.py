from django.shortcuts import render
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from .models import Post, PostImage, Comment, Wishlist
from .serializers import PostSerializer, CommentSerializer, WishlistSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser

# Create your views here.

class PostListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        posts = Post.objects.filter(approval=True).order_by('-created_at')
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            post = serializer.save(user=request.user)

            # Handle multiple image uploads
            images = request.FILES.getlist('images')
            for image in images:
                PostImage.objects.create(post=post, image=image)

            # Re-serialize to include the newly created images
            response_serializer = PostSerializer(post)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class CommentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, post_id):
        comments = Comment.objects.filter(post_id=post_id).order_by('-created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, post_id):
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, post_id=post_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class PostLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        post = Post.objects.get(id=post_id)
        if post.likes.filter(id=request.user.id).exists():
            post.likes.remove(request.user)
            return Response({'message': 'Post disliked successfully'}, status=status.HTTP_200_OK)
        else:
            post.likes.add(request.user)
            return Response({'message': 'Post liked successfully'}, status=status.HTTP_200_OK)
    
    def get(self, request, post_id):
        post = Post.objects.get(id=post_id)
        return Response({'likes': post.likes.count()})
    
class WishListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # Get all wishlisted posts by the logged-in user
    def get(self, request):
        wishlists = Wishlist.objects.filter(user=request.user).order_by('-created_at')
        serializer = WishlistSerializer(wishlists, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        wishlist = Wishlist.objects.filter(post=post, user=request.user)

        if wishlist.exists():
            wishlist.delete()
            return Response({"message": "Removed from wishlist"}, status=status.HTTP_200_OK)
        else:
            Wishlist.objects.create(post=post, user=request.user)
            return Response({"message": "Added to wishlist"}, status=status.HTTP_201_CREATED)



class FilteredPostView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        category = request.query_params.get('category')
        occasion = request.query_params.get('occasion')
        target = request.query_params.get('target')

        posts = Post.objects.filter(approval=True)  # base queryset

        if category:
            posts = posts.filter(category_id=category)

        if occasion:
            posts = posts.filter(occasion_id=occasion)

        if target:
            posts = posts.filter(target_category=target)

        serializer = PostSerializer(posts.order_by('-created_at'), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PostSearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('query', '').strip()

        if not query:
            return Response([], status=status.HTTP_200_OK)

        posts = Post.objects.filter(
            Q(approval=True) & (
                Q(content__icontains=query) |
                Q(category__name__icontains=query) |
                Q(occasion__name__icontains=query) |
                Q(target_category__icontains=query)
            )
        ).order_by('-created_at')

        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TrendingPostView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        one_month_ago = timezone.now() - timedelta(days=30)

        posts = Post.objects.filter(
            approval=True,
            created_at__gte=one_month_ago
        ).annotate(
            likes_count=Count('likes'),
            comments_count=Count('comment'),
            engagement=Count('likes') + Count('comment')
        ).order_by('-engagement', '-created_at')

        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecommendedPostView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Collect post IDs the user has engaged with
        liked_posts = Post.objects.filter(likes=user)
        commented_posts = Post.objects.filter(comment__user=user)
        wishlisted_posts = Post.objects.filter(wishlisted_by__user=user)

        engaged_posts = liked_posts | commented_posts | wishlisted_posts
        engaged_post_ids = engaged_posts.values_list('id', flat=True).distinct()

        # Extract user interests from engaged posts
        categories = engaged_posts.values_list('category', flat=True).distinct()
        occasions = engaged_posts.values_list('occasion', flat=True).distinct()
        targets = engaged_posts.values_list('target_category', flat=True).distinct()

        # Filter out None values
        categories = [c for c in categories if c is not None]
        occasions = [o for o in occasions if o is not None]
        targets = [t for t in targets if t]

        # If user has no engagement history, return empty
        if not categories and not occasions and not targets:
            return Response([], status=status.HTTP_200_OK)

        # Build Q filter for matching interests
        interest_filter = Q()
        if categories:
            interest_filter |= Q(category_id__in=categories)
        if occasions:
            interest_filter |= Q(occasion_id__in=occasions)
        if targets:
            interest_filter |= Q(target_category__in=targets)

        # Get recommended posts: approved, matching interests, not already engaged
        posts = Post.objects.filter(
            Q(approval=True) & interest_filter
        ).exclude(
            id__in=engaged_post_ids
        ).order_by('-created_at')

        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

