from django.db import models
from django.contrib.auth.models import User
from ckeditor_uploader.fields import RichTextUploadingField
from django.utils.text import slugify
from django.urls import reverse
from taggit.managers import TaggableManager
from accounts.models import StudentProfile

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class News(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    author = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='news_posts')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='news')
    featured_image = models.ImageField(upload_to='news/images/')
    summary = models.TextField(max_length=500)
    content = RichTextUploadingField()
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    publish_date = models.DateTimeField(blank=True, null=True)
    tags = TaggableManager()
    views = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "News"
        ordering = ["-publish_date"]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('news:news_detail', kwargs={'slug': self.slug})
    
    def increase_views(self):
        self.views += 1
        self.save(update_fields=['views'])

    def approved_comments(self):
        return self.comments.filter(is_approved=True)

class Comment(models.Model):
    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Comment by {self.user} on {self.news}'
