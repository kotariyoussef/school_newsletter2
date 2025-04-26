"""
analytics/utils.py
Analytics utility functions for the newsletter website
"""
from django.db.models import Count, Sum, Avg, F, Q, ExpressionWrapper, fields
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta
import pandas as pd
import numpy as np
from collections import Counter

from news.models import News, Category, Comment
from accounts.models import StudentProfile


def get_top_articles(days=30, limit=10):
    """
    Get the top viewed articles within a specified time period
    
    Args:
        days (int): Number of days to look back
        limit (int): Number of articles to return
        
    Returns:
        QuerySet: Top articles by view count
    """
    period_start = timezone.now() - timedelta(days=days)
    return News.objects.filter(
        status='published',
        publish_date__gte=period_start
    ).order_by('-views')[:limit]


def get_category_distribution():
    """
    Get distribution of articles across categories
    
    Returns:
        dict: Categories with article counts
    """
    return dict(
        News.objects.filter(status='published')
        .values('category__name')
        .annotate(count=Count('id'))
        .order_by('-count')
        .values_list('category__name', 'count')
    )


def get_engagement_metrics(days=30):
    """
    Calculate engagement metrics for the past specified days
    
    Args:
        days (int): Number of days to look back
        
    Returns:
        dict: Dictionary containing various engagement metrics
    """
    period_start = timezone.now() - timedelta(days=days)
    published_articles = News.objects.filter(
        status='published',
        publish_date__gte=period_start
    )
    
    total_articles = published_articles.count()
    total_views = published_articles.aggregate(total=Sum('views'))['total'] or 0
    total_comments = Comment.objects.filter(
        news__in=published_articles,
        created_at__gte=period_start
    ).count()
    
    # Calculate averages
    avg_views_per_article = total_views / total_articles if total_articles > 0 else 0
    avg_comments_per_article = total_comments / total_articles if total_articles > 0 else 0
    
    return {
        'total_articles': total_articles,
        'total_views': total_views,
        'total_comments': total_comments,
        'avg_views_per_article': avg_views_per_article,
        'avg_comments_per_article': avg_comments_per_article
    }


def get_author_performance(days=30, limit=10):
    """
    Get top performing authors based on article views and comments
    
    Args:
        days (int): Number of days to look back
        limit (int): Number of authors to return
        
    Returns:
        QuerySet: Top authors with performance metrics
    """
    period_start = timezone.now() - timedelta(days=days)
    
    return StudentProfile.objects.filter(
        news_posts__status='published',
        news_posts__publish_date__gte=period_start
    ).annotate(
        article_count=Count('news_posts', distinct=True),
        total_views=Sum('news_posts__views'),
        comment_count=Count('news_posts__comments')
    ).order_by('-total_views')[:limit]


def get_time_series_data(metric_type='views', interval='day', days=30):
    """
    Get time series data for specified metric and time interval
    
    Args:
        metric_type (str): Type of metric ('views', 'posts', 'comments')
        interval (str): Time interval ('day', 'week', 'month')
        days (int): Number of days to look back
        
    Returns:
        dict: Time series data for the specified metric
    """
    period_start = timezone.now() - timedelta(days=days)
    
    # Select appropriate truncation function based on interval
    if interval == 'day':
        trunc_func = TruncDay
    elif interval == 'week':
        trunc_func = TruncWeek
    else:  # month
        trunc_func = TruncMonth
    
    if metric_type == 'views':
        # For views, we need to calculate based on the current view count
        # This is an approximation as we don't track when views occurred
        articles = News.objects.filter(
            status='published',
            publish_date__gte=period_start
        ).annotate(
            period=trunc_func('publish_date')
        ).values('period').annotate(
            count=Sum('views')
        ).order_by('period')
        
    elif metric_type == 'posts':
        # For posts, we count the number published in each time period
        articles = News.objects.filter(
            status='published',
            publish_date__gte=period_start
        ).annotate(
            period=trunc_func('publish_date')
        ).values('period').annotate(
            count=Count('id')
        ).order_by('period')
        
    elif metric_type == 'comments':
        # For comments, count comments made in each time period
        articles = Comment.objects.filter(
            created_at__gte=period_start
        ).annotate(
            period=trunc_func('created_at')
        ).values('period').annotate(
            count=Count('id')
        ).order_by('period')
    
    # Convert to dictionary format
    result = {item['period'].strftime('%Y-%m-%d'): item['count'] for item in articles}
    
    return result


def get_tag_popularity(limit=20):
    """
    Get the most popular tags used in articles
    
    Args:
        limit (int): Number of tags to return
        
    Returns:
        list: List of dictionaries with tag names and counts
    """
    from taggit.models import Tag
    
    tags = Tag.objects.annotate(
        article_count=Count('news')
    ).order_by('-article_count')[:limit]
    
    return [{'name': tag.name, 'count': tag.article_count} for tag in tags]


def get_reader_retention(days=90):
    """
    Analyze reader retention by looking at returning commenters
    
    Args:
        days (int): Number of days to analyze
        
    Returns:
        dict: Retention metrics
    """
    period_start = timezone.now() - timedelta(days=days)
    
    # Get commenters who commented multiple times
    commenters = Comment.objects.filter(
        created_at__gte=period_start
    ).values('user').annotate(
        comment_count=Count('id')
    ).order_by('-comment_count')
    
    # Calculate retention metrics
    single_commenters = sum(1 for c in commenters if c['comment_count'] == 1)
    returning_commenters = sum(1 for c in commenters if c['comment_count'] > 1)
    highly_engaged = sum(1 for c in commenters if c['comment_count'] >= 5)
    
    total_commenters = single_commenters + returning_commenters
    retention_rate = (returning_commenters / total_commenters * 100) if total_commenters > 0 else 0
    
    return {
        'total_commenters': total_commenters,
        'single_commenters': single_commenters,
        'returning_commenters': returning_commenters,
        'highly_engaged': highly_engaged,
        'retention_rate': retention_rate
    }


def get_content_performance_by_length():
    """
    Analyze article performance based on content length
    
    Returns:
        dict: Performance metrics grouped by content length
    """
    # Add content length field
    articles = News.objects.filter(status='published').annotate(
        content_length=ExpressionWrapper(
            F('content').length(), output_field=fields.IntegerField()
        )
    )
    
    # Define length categories
    short = articles.filter(content_length__lt=1000).aggregate(
        count=Count('id'),
        avg_views=Avg('views')
    )
    
    medium = articles.filter(
        content_length__gte=1000, 
        content_length__lt=3000
    ).aggregate(
        count=Count('id'),
        avg_views=Avg('views')
    )
    
    long = articles.filter(content_length__gte=3000).aggregate(
        count=Count('id'),
        avg_views=Avg('views')
    )
    
    return {
        'short': short,
        'medium': medium,
        'long': long
    }


def generate_content_recommendations(category_id=None, tag=None):
    """
    Generate content recommendations based on popularity and relevance
    
    Args:
        category_id (int, optional): Category ID to focus recommendations
        tag (str, optional): Tag to focus recommendations
        
    Returns:
        QuerySet: Recommended articles
    """
    base_qs = News.objects.filter(status='published')
    
    if category_id:
        base_qs = base_qs.filter(category_id=category_id)
    
    if tag:
        base_qs = base_qs.filter(tags__name__in=[tag])
    
    # Get popular articles from the last 30 days
    period_start = timezone.now() - timedelta(days=30)
    
    return base_qs.filter(
        publish_date__gte=period_start
    ).order_by('-views', '-publish_date')[:10]


def export_analytics_data(start_date=None, end_date=None, format='csv'):
    """
    Export analytics data for the specified time period
    
    Args:
        start_date (datetime, optional): Start date for data
        end_date (datetime, optional): End date for data
        format (str): Export format ('csv' or 'json')
        
    Returns:
        str: Path to the exported file
    """
    if not start_date:
        start_date = timezone.now() - timedelta(days=30)
    
    if not end_date:
        end_date = timezone.now()
    
    # Get articles data
    articles = News.objects.filter(
        status='published',
        publish_date__gte=start_date,
        publish_date__lte=end_date
    ).values(
        'id', 'title', 'slug', 'author__user__username', 
        'category__name', 'views', 'publish_date'
    )
    
    # Convert to pandas DataFrame
    df = pd.DataFrame(list(articles))
    
    # Add comment counts
    comment_counts = {}
    for article in News.objects.filter(id__in=df['id']):
        comment_counts[article.id] = article.comments.count()
    
    df['comment_count'] = df['id'].map(comment_counts)
    
    # Export to the specified format
    filename = f"analytics_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
    
    if format == 'csv':
        file_path = f"{filename}.csv"
        df.to_csv(file_path, index=False)
    else:  # json
        file_path = f"{filename}.json"
        df.to_json(file_path, orient='records')
    
    return file_path


def calculate_article_read_time():
    """
    Calculate estimated read time for all articles
    
    Returns:
        dict: Dictionary mapping article IDs to estimated read times in minutes
    """
    WORDS_PER_MINUTE = 200
    
    articles = News.objects.filter(status='published').annotate(
        content_length=ExpressionWrapper(
            F('content').length(), output_field=fields.IntegerField()
        )
    )
    
    read_times = {}
    for article in articles:
        # Rough estimate: 5 characters per word
        word_count = article.content_length / 5
        read_time = max(1, round(word_count / WORDS_PER_MINUTE))
        read_times[article.id] = read_time
    
    return read_times


def find_trending_topics():
    """
    Analyze recent content to identify trending topics
    
    Returns:
        list: List of trending topics with weights
    """
    # Get recent articles from the past 14 days
    recent_period = timezone.now() - timedelta(days=14)
    recent_articles = News.objects.filter(
        status='published',
        publish_date__gte=recent_period
    )
    
    # Collect all tags
    all_tags = []
    for article in recent_articles:
        all_tags.extend([tag.name for tag in article.tags.all()])
    
    # Count occurrences
    tag_counts = Counter(all_tags)
    
    # Convert to list of dictionaries and sort
    trending_topics = [{'topic': tag, 'count': count} 
                      for tag, count in tag_counts.items()]
    trending_topics.sort(key=lambda x: x['count'], reverse=True)
    
    return trending_topics[:15]  # Return top 15 trending topics