# urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard URLs
    path('', views.writer_dashboard, name='writer_dashboard'),
    path('posts/', views.post_list, name='post_list'),
    path('posts/create/', views.create_post, name='create_post'),
    path('posts/<slug:slug>/edit/', views.edit_post, name='edit_post'),
    path('posts/<slug:slug>/analytics/', views.post_analytics, name='post_analytics'),
    path('comments/', views.manage_comments, name='manage_comments'),
    path('comments/<int:comment_id>/approve/', views.approve_comment, name='approve_comment'),
    path('comments/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
]