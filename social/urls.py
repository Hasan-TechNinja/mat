from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<int:post_id>/comments/', views.CommentListCreateView.as_view(), name='comment-list-create'),
    path('posts/<int:post_id>/likes/', views.PostLikeView.as_view(), name='post-likes'),
    path('post/<int:post_id>/wishlist/', views.WishListView.as_view(), name='wishlist'),
    path('post/wishlist/', views.WishListView.as_view(), name='wishlist'),
    path('posts/filter/', views.FilteredPostView.as_view(), name='filtered-posts'),
]