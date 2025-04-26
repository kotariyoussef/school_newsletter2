from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, F, Count, Prefetch
from django.core.cache import cache
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from datetime import timedelta

from .models import News, Category, Comment
from taggit.models import Tag
from .forms import NewsForm, CommentForm

class ContactView(TemplateView):
    template_name = "contact.html"

def home_view(request):
    """
    Home page view displaying featured, latest, and popular news articles
    organized by categories and other relevant content.
    """
    # Try to get homepage data from cache first
    cache_key = 'homepage_data'
    homepage_data = cache.get(cache_key)
    
    if not homepage_data:
        # Get latest news articles
        latest_articles = News.objects.select_related('author', 'category').prefetch_related('tags').filter(
            status='published'
        ).order_by('-publish_date')[:10]
        
        # Compile all data
        homepage_data = {
            'latest_articles': latest_articles
        }
        
        # Cache for 15 minutes
        cache.set(cache_key, homepage_data, 15 * 60)
    
    # Add non-cached data
    context = homepage_data.copy()
    
    # Check if user is authenticated for personalized content
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        # Get recommended articles based on user's reading history or preferences
        # This is kept out of cache as it's personalized
        user_profile = request.user.userprofile
        
        # Get user's favorite categories if they exist
        if hasattr(user_profile, 'favorite_categories'):
            favorite_categories = user_profile.favorite_categories.all()
            recommended_articles = News.objects.select_related('author', 'category').filter(
                status='published',
                publish_date__lte=timezone.now(),
                category__in=favorite_categories
            ).exclude(
                id__in=[article.id for article in context['latest_articles']]
            ).order_by('-publish_date')[:4]
            
            context['recommended_articles'] = recommended_articles
    
    return render(request, 'news/home.html', context)

class NewsListView(ListView):
    model = News
    template_name = 'news/news_list.html'
    context_object_name = 'news_list'
    paginate_by = 10
    
    def get_queryset(self):
        # Start with optimized query with select_related for foreign keys
        queryset = News.objects.select_related('author', 'category').prefetch_related('tags')
        
        # Filter published content
        queryset = queryset.filter(status='published')
        
        # Filter by category if specified
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            # Use cache for categories to reduce DB hits
            cache_key = f'category_{category_slug}'
            category = cache.get(cache_key)
            if not category:
                category = get_object_or_404(Category, slug=category_slug)
                cache.set(cache_key, category, 60*60)  # Cache for 1 hour
            queryset = queryset.filter(category=category)
        
        # Filter by tag if specified
        tag_slug = self.kwargs.get('tag_slug')
        if tag_slug:
            # Use cache for tags
            cache_key = f'tag_{tag_slug}'
            tag = cache.get(cache_key)
            if not tag:
                tag = get_object_or_404(Tag, slug=tag_slug)
                cache.set(cache_key, tag, 60*60)  # Cache for 1 hour
            queryset = queryset.filter(tags__slug=tag.slug)
        
        # Filter by search query if specified
        search_query = self.request.GET.get('q')
        if search_query:
            # Improved search with trigram similarity if postgres is used
            # Can be extended with django.contrib.postgres.search for better full-text search
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(summary__icontains=search_query) |
                Q(content__icontains=search_query)
            ).distinct()
        
        # Filter by date range if specified
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(publish_date__gte=date_from)
            
        # Sort options
        sort_by = self.request.GET.get('sort', '-publish_date')  # Default sort by newest
        allowed_sort_fields = ['publish_date', 'title', 'views', '-publish_date', '-title', '-views']
        
        if sort_by in allowed_sort_fields:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-publish_date')  # Default fallback
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Cache categories for 1 hour
        cache_key = 'all_categories'
        categories = cache.get(cache_key)
        if not categories:
            categories = Category.objects.all()
            cache.set(cache_key, categories, 60*60)
        context['categories'] = categories
        
        # Cache featured news for 10 minutes
        cache_key = 'featured_news'
        featured_news = cache.get(cache_key)
        if not featured_news:
            featured_news = News.objects.select_related('author', 'category').filter(
                status='published', is_featured=True
            ).order_by('-publish_date')[:5]
            cache.set(cache_key, featured_news, 10*60)
        context['featured_news'] = featured_news
        
        # Popular news (most viewed in last week)
        cache_key = 'popular_news'
        popular_news = cache.get(cache_key)
        if not popular_news:
            week_ago = timezone.now() - timedelta(days=7)
            popular_news = News.objects.select_related('author', 'category').filter(
                status='published',
                publish_date__gte=week_ago
            ).order_by('-views')[:5]
            cache.set(cache_key, popular_news, 3*60*60)  # Cache for 3 hours
        context['popular_news'] = popular_news
        
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            cache_key = f'category_{category_slug}'
            current_category = cache.get(cache_key)
            if not current_category:
                current_category = get_object_or_404(Category, slug=category_slug)
                cache.set(cache_key, current_category, 60*60)
            context['current_category'] = current_category
        
        tag_slug = self.kwargs.get('tag_slug')
        if tag_slug:
            cache_key = f'tag_{tag_slug}'
            current_tag = cache.get(cache_key)
            if not current_tag:
                current_tag = get_object_or_404(Tag, slug=tag_slug)
                cache.set(cache_key, current_tag, 60*60)
            context['current_tag'] = current_tag
        
        # Add filter contexts
        context['search_query'] = self.request.GET.get('q', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['sort_by'] = self.request.GET.get('sort', '-publish_date')
        
        # Recent tags
        cache_key = 'recent_tags'
        recent_tags = cache.get(cache_key)
        if not recent_tags:
            recent_tags = Tag.objects.all()[:10]
            cache.set(cache_key, recent_tags, 60*60)
        context['recent_tags'] = recent_tags
        
        return context

class NewsDetailView(DetailView):
    model = News
    template_name = 'news/news_detail.html'
    context_object_name = 'news'
    
    def get_queryset(self):
        # Optimize with select_related and prefetch_related
        queryset = News.objects.select_related('author', 'category').prefetch_related(
            Prefetch(
                'comments',
                queryset=Comment.objects.select_related('user').filter(is_approved=True).order_by('-created_at'),
                to_attr='approved_comments'
            ),
            'tags'
        )
        
        if self.request.user.is_staff:
            # Staff can see all news, including drafts
            return queryset
        # Regular users can only see published news
        return queryset.filter(status='published')
    
    def get_object(self, queryset=None):
        # Try to get from cache first (useful for high-traffic sites)
        slug = self.kwargs.get(self.slug_url_kwarg)
        cache_key = f'news_detail_{slug}'
        news = cache.get(cache_key)
        
        if not news:
            news = super().get_object(queryset)
            # Cache for 30 minutes, content management can override cache
            cache.set(cache_key, news, 30*60)
            
        return news
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        news = self.get_object()
        
        # Use F() expression to avoid race conditions when incrementing counters
        News.objects.filter(pk=news.pk).update(views=F('views') + 1)
        # Update the object in the context to reflect the change
        news.views += 1
        
        # Get related news from cache or DB
        cache_key = f'related_news_{news.pk}'
        related_news = cache.get(cache_key)
        if not related_news:
            # Find related news by category and tags
            related_by_category = News.objects.select_related('author', 'category').filter(
                status='published', 
                category=news.category
            ).exclude(id=news.id).distinct()
            
            # Get news with similar tags
            news_tags = news.tags.names()
            related_by_tags = News.objects.select_related('author', 'category').filter(
                status='published',
                tags__name__in=news_tags
            ).exclude(id=news.id).distinct()
            
            # Combine and limit
            related_news = (related_by_category | related_by_tags).distinct()
            cache.set(cache_key, related_news, 30*60)  # Cache for 30 minutes
            
        context['related_news'] = related_news
        
        # Use preloaded comments from prefetch_related
        context['comments'] = getattr(news, 'approved_comments', [])
        context['comment_form'] = CommentForm()

                # Cache categories for 1 hour
        cache_key = 'all_categories'
        categories = cache.get(cache_key)
        if not categories:
            categories = Category.objects.all()
            cache.set(cache_key, categories, 60*60)
        context['categories'] = categories
        
        # Cache featured news for 10 minutes
        cache_key = 'featured_news'
        featured_news = cache.get(cache_key)
        if not featured_news:
            featured_news = News.objects.select_related('author', 'category').filter(
                status='published', is_featured=True
            ).order_by('-publish_date')[:5]
            cache.set(cache_key, featured_news, 10*60)
        context['featured_news'] = featured_news
        
        return context

class NewsCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = News
    form_class = NewsForm
    template_name = 'news/news_form.html'
    
    def test_func(self):
        # Only staff members or users with approved profiles can create news
        return (self.request.user.is_staff or 
                hasattr(self.request.user, 'profile'))
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = kwargs.get('initial', {})
        kwargs['initial']['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.author = self.request.user.profile
        response = super().form_valid(form)
        
        # Clear category and tag caches when new content is added
        cache.delete('all_categories')
        cache.delete('featured_news')
        cache.delete('recent_tags')
        
        messages.success(self.request, 'News post created successfully!')
        return response

class NewsUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = News
    form_class = NewsForm
    template_name = 'news/news_form.html'
    
    def test_func(self):
        news = self.get_object()
        # Only staff members or the author can update news
        return self.request.user.is_staff or (
            hasattr(self.request.user, 'profile') and 
            self.request.user.profile == news.author
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = kwargs.get('initial', {})
        kwargs['initial']['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Clear relevant caches
        news = self.get_object()
        cache.delete(f'news_detail_{news.slug}')
        cache.delete('featured_news')
        cache.delete(f'related_news_{news.pk}')
        
        messages.success(self.request, 'News post updated successfully!')
        return response

class NewsDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = News
    template_name = 'news/news_confirm_delete.html'
    success_url = reverse_lazy('news:news_list')
    
    def test_func(self):
        news = self.get_object()
        # Only staff members or the author can delete news
        return self.request.user.is_staff or (
            hasattr(self.request.user, 'profile') and 
            self.request.user.profile == news.author
        )
    
    def delete(self, request, *args, **kwargs):
        news = self.get_object()
        
        # Clear relevant caches
        cache.delete(f'news_detail_{news.slug}')
        cache.delete('featured_news')
        cache.delete(f'related_news_{news.pk}')
        cache.delete('popular_news')
        
        messages.success(self.request, 'News post deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
@require_POST
def add_comment(request, slug):
    news = get_object_or_404(News, slug=slug, status='published')
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.news = news
            comment.user = request.user
            # Auto-approve comments from staff
            if request.user.is_staff:
                comment.is_approved = True
            comment.save()
            
            # Clear comment cache
            cache.delete(f'news_detail_{slug}')
            
            messages.success(request, 'Your comment has been submitted and is awaiting approval.')
            
            # Handle AJAX requests
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Comment submitted successfully',
                    'is_approved': comment.is_approved
                })
        else:
            messages.error(request, 'There was an error submitting your comment.')
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'errors': form.errors
                }, status=400)
    
    return redirect(news.get_absolute_url())

@login_required
def toggle_favorite(request, slug):
    """Toggle favorite status of a news post for a user."""
    if not hasattr(request.user, 'profile'):
        return JsonResponse({'status': 'error', 'message': 'User profile not found'}, status=400)
    
    news = get_object_or_404(News, slug=slug, status='published')
    profile = request.user.profile
    
    # Assuming there's a ManyToMany relationship between profile and News
    # Add this field to your profile model if needed
    if news in profile.favorite_news.all():
        profile.favorite_news.remove(news)
        is_favorite = False
    else:
        profile.favorite_news.add(news)
        is_favorite = True
    
    return JsonResponse({
        'status': 'success', 
        'is_favorite': is_favorite
    })

class DraftNewsListView(LoginRequiredMixin, ListView):
    """View for listing a user's draft news posts."""
    model = News
    template_name = 'news/draft_news_list.html'
    context_object_name = 'draft_news'
    paginate_by = 10
    
    def get_queryset(self):
        # If user is staff, show all drafts, otherwise only user's drafts
        if self.request.user.is_staff:
            return News.objects.select_related('author', 'category').filter(status='draft')
        
        # Regular users see only their own drafts
        if hasattr(self.request.user, 'profile'):
            return News.objects.select_related('author', 'category').filter(
                status='draft',
                author=self.request.user.profile
            )
        return News.objects.none()