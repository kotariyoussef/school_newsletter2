# news/context_processors.py

from django.utils import timezone
from django.db.models import Count, Q
from django.conf import settings
from django.core.cache import cache
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType

from .models import News, Category
from taggit.models import Tag

def news_context(request):
    """
    Context processor that provides common data for news templates.
    Implements the same caching strategy used in views.
    """
    if settings.DEBUG:
        cache.clear()
    context = {}

    context['site_name'] = settings.SITE_NAME
    context['site_description'] = settings.SITE_DESCRIPTION
    
    # Current user context
    if request.user.is_authenticated:
        context['is_staff'] = request.user.is_staff
        context['is_writer'] = (request.user.is_staff or 
                               (hasattr(request.user, 'userprofile') and 
                                request.user.userprofile.is_approved))
                                
        # Get user's favorite news if they have a profile
        if hasattr(request.user, 'userprofile'):
            # Only fetch IDs to make this lightweight
            favorite_ids = list(request.user.userprofile.favorite_news.values_list('id', flat=True))
            context['favorite_news_ids'] = favorite_ids
            
            # For staff users, get their draft count
            if context['is_writer']:
                draft_count = News.objects.filter(
                    author=request.user.userprofile,
                    status='draft'
                ).count()
                context['draft_count'] = draft_count
    
    # Categories (cached for 1 hour)
    cache_key = 'all_categories'
    categories = cache.get(cache_key)
    if not categories:
        categories = Category.objects.annotate(news_count=Count('news', 
            filter=Q(news__status='published', news__publish_date__lte=timezone.now())
        )).order_by('name')
        cache.set(cache_key, categories, 60*60)  # 1 hour
    context['categories'] = categories
    
    # Featured news (cached for 10 minutes)
    cache_key = 'featured_news'
    featured_news = cache.get(cache_key)
    if not featured_news:
        featured_news = News.objects.select_related('author', 'category').filter(
            status='published', 
            is_featured=True, 
            publish_date__lte=timezone.now()
        ).order_by('-publish_date')[:5]
        cache.set(cache_key, featured_news, 10*60)  # 10 minutes
    context['featured_news'] = featured_news
    
    # Popular news (cached for 3 hours)
    cache_key = 'popular_news'
    popular_news = cache.get(cache_key)
    if not popular_news:
        week_ago = timezone.now() - timedelta(days=7)
        popular_news = News.objects.select_related('author', 'category').filter(
            status='published',
            publish_date__gte=week_ago,
            publish_date__lte=timezone.now()
        ).order_by('-views')[:5]
        cache.set(cache_key, popular_news, 3*60*60)  # 3 hours
    context['popular_news'] = popular_news
    
    # Tags
    news_tags = Tag.objects.all()[:10]
    context['news_tags'] = news_tags
    
    # Latest news (cached for 5 minutes)
    cache_key = 'latest_news'
    latest_news = cache.get(cache_key)
    if not latest_news:
        latest_news = News.objects.select_related('author', 'category').filter(
            status='published',
            publish_date__lte=timezone.now()
        ).order_by('-publish_date')[:6]
        cache.set(cache_key, latest_news, 5*60)  # 5 minutes
    context['latest_news'] = latest_news
    
    # Get current date for date-based filtering
    context['current_date'] = timezone.now().date()
    context['week_ago'] = (timezone.now() - timedelta(days=7)).date()
    context['month_ago'] = (timezone.now() - timedelta(days=30)).date()
    
    # Top categories (with most news items)
    cache_key = 'top_categories'
    top_categories = cache.get(cache_key)
    if not top_categories:
        top_categories = Category.objects.annotate(
            news_count=Count('news', filter=Q(news__status='published', news__publish_date__lte=timezone.now()))
        ).filter(news_count__gt=0).order_by('-news_count')[:5]
        cache.set(cache_key, top_categories, 3*60*60)  # 3 hours
    context['top_categories'] = top_categories
    
    # Search form context
    if 'q' in request.GET:
        context['search_query'] = request.GET.get('q', '')
    
    # Check if this is a detail page
    if request.resolver_match and request.resolver_match.url_name == 'news_detail':
        slug = request.resolver_match.kwargs.get('slug')
        if slug:
            # Flag to let templates know we're on a detail page
            context['is_detail_page'] = True
            context['current_news_slug'] = slug
            
            # Get news object from cache or view context if available
            # This avoids duplicate DB calls if the view has already fetched it
            if hasattr(request, 'news_object'):
                context['current_news'] = request.news_object
            else:
                # Try to get from cache - we don't fetch from DB here to avoid 
                # duplicating the detailed query that view will perform anyway
                cache_key = f'news_detail_{slug}'
                news = cache.get(cache_key)
                if news:
                    context['current_news'] = news
    
    return context