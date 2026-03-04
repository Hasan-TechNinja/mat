from unicodedata import name
from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('posts/', views.PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<int:post_id>/comments/', views.CommentListCreateView.as_view(), name='comment-list-create'),
    path('comment/detail/<int:id>/', views.CommentDetailView.as_view(), name="comment-detail"),
    path('posts/<int:post_id>/likes/', views.PostLikeView.as_view(), name='post-likes'),
    path('post/<int:post_id>/wishlist/', views.WishListView.as_view(), name='wishlist'),
    path('post/wishlist/', views.WishListView.as_view(), name='wishlist'),
    path('posts/filter/', views.FilteredPostView.as_view(), name='filtered-posts'),
    path('posts/search/', views.PostSearchView.as_view(), name='post-search'),
    path('posts/trending/', views.TrendingPostView.as_view(), name='trending-posts'),
    path('posts/recommended/', views.RecommendedPostView.as_view(), name='recommended-posts'),
    path('occasions/', views.OccasionListView.as_view(), name='occasion-list'),
    path('community-activity/', views.CommunityActivityView.as_view(), name='community-activity'),
    path('posts/<int:post_id>/link-click/', views.PostLinkClickView.as_view(), name='post-link-click'),
    path('posts/top-clicked/', views.TopClickedPostView.as_view(), name='top-clicked-posts'),
    path('user/stats/', views.UserStatsView.as_view(), name='user-stats'),
    path('user/post-statuses/', views.UserPostStatusCountView.as_view(), name='user-post-statuses'),
    path('user/link-engagement/', views.LinkEngagementView.as_view(), name='user-link-engagement'),
]