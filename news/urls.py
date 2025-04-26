from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('', views.NewsListView.as_view(), name='news_list'),
    path('search/', views.NewsListView.as_view(), name='news_search'),
    path('category/<slug:category_slug>/', views.NewsListView.as_view(), name='news_by_category'),
    path('tag/<slug:tag_slug>/', views.NewsListView.as_view(), name='news_by_tag'),
    path('create/', views.NewsCreateView.as_view(), name='news_create'),
    path('<slug:slug>/', views.NewsDetailView.as_view(), name='news_detail'),
    path('<slug:slug>/edit/', views.NewsUpdateView.as_view(), name='news_update'),
    path('<slug:slug>/delete/', views.NewsDeleteView.as_view(), name='news_delete'),
    path('<slug:slug>/comment/', views.add_comment, name='add_comment'),
]