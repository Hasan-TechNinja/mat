from rest_framework.decorators import permission_classes
from django.shortcuts import render
from django.db.models import Q, Count, Sum
from django.db.models.functions import ExtractMonth
from django.utils import timezone
from datetime import timedelta
from .models import Post, PostImage, Comment, Wishlist, Category, Occasion
from django.contrib.auth.models import User
from .serializers import PostSerializer, CommentSerializer, WishlistSerializer, CategorySerializer, OccasionSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from notification.fcm_utils import send_push_notification
from .utils import fetch_amazon_product_data

# Create your views here.

class PostListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        posts = Post.objects.filter(approval=True).order_by('-created_at')
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        serializer = PostSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            save_kwargs = {'user': request.user}
            amazon_link = serializer.validated_data.get('amazon_link')
            
            if amazon_link:
                is_subscribed = False
                user_subs = request.user.subscriptions.select_related('plan').filter(status='active')
                for sub in user_subs:
                    if sub.is_active_subscription and sub.plan.slug.lower() == 'pro':
                        is_subscribed = True
                        break
                
                if not is_subscribed:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(amazon_link)
                    query_params = urllib.parse.parse_qs(parsed.query)
                    query_params['tag'] = ['giftmedia-21']
                    new_query = urllib.parse.urlencode(query_params, doseq=True)
                    save_kwargs['amazon_link'] = parsed._replace(query=new_query).geturl()

                # Fetch Amazon metadata
                title, image_url = fetch_amazon_product_data(save_kwargs.get('amazon_link', amazon_link))
                if title:
                    save_kwargs['amazon_product_name'] = title
                if image_url:
                    save_kwargs['amazon_product_image_url'] = image_url

            post = serializer.save(**save_kwargs)

            # Handle multiple image uploads
            images = request.FILES.getlist('images')
            for image in images:
                PostImage.objects.create(post=post, image=image)

            # Re-serialize to include the newly created images
            response_serializer = PostSerializer(post, context={'request': request})
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

            # Send notification to post owner
            try:
                post = Post.objects.get(id=post_id)
                if post.user != request.user:
                    send_push_notification(
                        user=post.user,
                        title="New Comment",
                        body=f"{request.user.username} commented on your post.",
                        data={"type": "comment", "post_id": str(post_id)}
                    )
                    print("Notification sent successfully")
            except Post.DoesNotExist:
                pass

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, id):
        try:
            return Comment.objects.get(id=id)
        except Comment.DoesNotExist:
            return None

    def get(self, request, id):
        comment = self.get_object(id)
        if comment is None:
            return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id):
        comment = self.get_object(id)
        if comment is None:
            return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        if comment.user != request.user:
            return Response({"error": "You can only edit your own comments"}, status=status.HTTP_403_FORBIDDEN)
        serializer = CommentSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        comment = self.get_object(id)
        if comment is None:
            return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        if comment.user != request.user:
            return Response({"error": "You can only delete your own comments"}, status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response({"message": "Comment deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class PostLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        post = Post.objects.get(id=post_id)
        if post.likes.filter(id=request.user.id).exists():
            post.likes.remove(request.user)
            return Response({'message': 'Post disliked successfully'}, status=status.HTTP_200_OK)
        else:
            post.likes.add(request.user)

            # Send notification to post owner
            if post.user != request.user:
                send_push_notification(
                    user=post.user,
                    title="New Like",
                    body=f"{request.user.username} liked your post.",
                    data={"type": "like", "post_id": str(post_id)}
                )

            return Response({'message': 'Post liked successfully'}, status=status.HTTP_200_OK)
    
    def get(self, request, post_id):
        post = Post.objects.get(id=post_id)
        return Response({'likes': post.likes.count()})
    
class WishListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # Get all wishlisted posts by the logged-in user
    def get(self, request):
        wishlists = Wishlist.objects.filter(user=request.user).order_by('-created_at')
        
        category = request.query_params.get('category')
        occasion = request.query_params.get('occasion')
        target = request.query_params.get('target')

        if category:
            wishlists = wishlists.filter(post__category_id=category)
        if occasion:
            wishlists = wishlists.filter(post__occasion_id=occasion)
        if target:
            wishlists = wishlists.filter(post__target_category=target)

        serializer = WishlistSerializer(wishlists, many=True, context={'request': request})
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

            # Send notification to post owner
            if post.user != request.user:
                send_push_notification(
                    user=post.user,
                    title="New Wishlist",
                    body=f"{request.user.username} wishlisted your post.",
                    data={"type": "wishlist", "post_id": str(post_id)}
                )

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

        serializer = PostSerializer(posts.order_by('-created_at'), many=True, context={'request': request})
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

        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class TrendingPostView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        one_month_ago = timezone.now() - timedelta(days=30)

        posts = Post.objects.filter(
            approval=True,
            created_at__gte=one_month_ago
        )

        category = request.query_params.get('category')
        occasion = request.query_params.get('occasion')
        target = request.query_params.get('target')

        if category:
            posts = posts.filter(category_id=category)
        if occasion:
            posts = posts.filter(occasion_id=occasion)
        if target:
            posts = posts.filter(target_category=target)

        posts = posts.annotate(
            likes_count=Count('likes'),
            comments_count=Count('comment'),
            engagement=Count('likes') + Count('comment')
        ).order_by('-engagement', '-created_at')

        serializer = PostSerializer(posts, many=True, context={'request': request, 'status': 'trending'})
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
        )

        category = request.query_params.get('category')
        occasion = request.query_params.get('occasion')
        target = request.query_params.get('target')

        if category:
            posts = posts.filter(category_id=category)
        if occasion:
            posts = posts.filter(occasion_id=occasion)
        if target:
            posts = posts.filter(target_category=target)

        posts = posts.order_by('-created_at')

        serializer = PostSerializer(posts, many=True, context={'request': request, 'status': 'recommended'})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoryListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        categories = Category.objects.all().order_by('name')
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OccasionListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        occasions = Occasion.objects.all().order_by('name')
        serializer = OccasionSerializer(occasions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CommunityActivityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        gift_founds = Post.objects.exclude(amazon_link__isnull=True).exclude(amazon_link__exact='').count()
        contributors = User.objects.filter(is_active=True).count()
        
        return Response({
            "gift_founds": gift_founds,
            "contributors": contributors
        }, status=status.HTTP_200_OK)


class PostLinkClickView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            post.link_clicks += 1
            post.save(update_fields=['link_clicks'])
            return Response({'message': 'Click incremented successfully', 'link_clicks': post.link_clicks}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)


class UserStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        stats = Post.objects.filter(user=user).aggregate(
            total_link_clicks=Sum('link_clicks'),
            total_likes=Count('likes')
        )
        
        return Response({
            'total_link_clicks': stats['total_link_clicks'] or 0,
            'total_likes': stats['total_likes'] or 0
        }, status=status.HTTP_200_OK)


class TopClickedPostView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        posts = Post.objects.filter(approval=True).order_by('-link_clicks', '-created_at')
        
        category = request.query_params.get('category')
        occasion = request.query_params.get('occasion')
        target = request.query_params.get('target')

        if category:
            posts = posts.filter(category_id=category)
        if occasion:
            posts = posts.filter(occasion_id=occasion)
        if target:
            posts = posts.filter(target_category=target)

        serializer = PostSerializer(posts, many=True, context={'request': request, 'status': 'top-clicked'})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserPostStatusCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Currently, the Post model only has an `approval` BooleanField.
        # True = Approved, False = Pending
        approved_count = Post.objects.filter(user=user, approval=True).count()
        pending_count = Post.objects.filter(user=user, approval=False).count()
        
        # Since there is no `rejected` field or status choice in the model, 
        # it will be returned as 0 for now.
        rejected_count = 0
        
        return Response({
            'approved': approved_count,
            'pending': pending_count,
            'rejected': rejected_count
        }, status=status.HTTP_200_OK)


class LinkEngagementView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        year_param = request.query_params.get('year')
        if not year_param:
            year = timezone.now().year
        else:
            try:
                year = int(year_param)
            except ValueError:
                return Response({"error": "Invalid year format"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        
        # Filter posts by user and the specified year
        posts = Post.objects.filter(user=user, created_at__year=year)
        
        # Aggregate link clicks grouped by month of post creation
        monthly_clicks = posts.annotate(month=ExtractMonth('created_at')) \
                              .values('month') \
                              .annotate(total_clicks=Sum('link_clicks')) \
                              .order_by('month')

        # Format the output to ensure all 12 months are included
        months_data = {i: 0 for i in range(1, 13)}
        for entry in monthly_clicks:
            months_data[entry['month']] = entry['total_clicks'] or 0

        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        data = []
        for i in range(1, 13):
            data.append({
                "month": month_names[i-1],
                "clicks": months_data[i]
            })

        return Response(data, status=status.HTTP_200_OK)


class MyPostView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        posts = Post.objects.filter(user=user).order_by('-created_at')
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            post.delete()
            return Response({'message': 'Post deleted successfully'}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)


class UserPostListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            user = User.objects.get(id=pk)
            
            # Default order is descending (newest first)
            order = request.query_params.get('order', 'desc').lower()
            
            if order == 'asc':
                posts = Post.objects.filter(user=user).order_by('created_at')
            else:
                posts = Post.objects.filter(user=user).order_by('-created_at')
                
            serializer = PostSerializer(posts, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)