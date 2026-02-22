from django.shortcuts import render
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
