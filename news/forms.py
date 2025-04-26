from django import forms
from django.utils.text import slugify
from django.utils import timezone
from taggit.forms import TagWidget
from ckeditor_uploader.widgets import CKEditorUploadingWidget

from .models import News, Comment, Category

class NewsForm(forms.ModelForm):
    """
    Form for creating and updating News articles.
    Uses CKEditorUploadingWidget for rich text editing and image uploads.
    Integrates with django-taggit for tag management.
    """
    # Add category as a ModelChoiceField to customize the queryset if needed
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select Category",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Use CKEditor for content
    content = forms.CharField(widget=CKEditorUploadingWidget())
    
    # Override the tags field to use TagWidget
    tags = forms.CharField(
        required=False,
        widget=TagWidget(attrs={'class': 'form-control', 'data-role': 'tagsinput'}),
        help_text="Enter tags separated by commas"
    )
    
    # Add publish date field with calendar widget
    publish_date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'},
            format='%Y-%m-%dT%H:%M'
        ),
        required=False,
        help_text="Leave empty to publish immediately"
    )
    
    # Add a checkbox for featured news
    is_featured = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = News
        fields = ['title', 'summary', 'content', 'category', 'tags', 
                 'status', 'publish_date', 'is_featured', 'featured_image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter title'}),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief summary of the news article'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'featured_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract user from initial data for potential later use
        initial = kwargs.get('initial', {})
        self.user = initial.pop('user', None)
        super(NewsForm, self).__init__(*args, **kwargs)
        
        # When editing an existing article
        if self.instance.pk and self.instance.publish_date:
            # Format the date for the datetime-local input
            self.initial['publish_date'] = self.instance.publish_date.strftime('%Y-%m-%dT%H:%M')
    
    def clean_slug(self):
        """
        Auto-generate slug from title if not provided.
        Ensure uniqueness by checking against existing slugs.
        """
        title = self.cleaned_data.get('title')
        slug = self.instance.slug or slugify(title)
        
        # Check for existing slug only when creating new article (not when updating)
        if not self.instance.pk:
            qs = News.objects.filter(slug=slug)
            if qs.exists():
                # Append timestamp to ensure uniqueness
                slug = f"{slug}-{int(timezone.now().timestamp())}"
        
        return slug
    
    def clean_publish_date(self):
        """
        Set current datetime if publish_date is not provided
        and status is 'published'.
        """
        publish_date = self.cleaned_data.get('publish_date')
        status = self.cleaned_data.get('status')
        
        if status == 'published' and not publish_date:
            publish_date = timezone.now()
            
        return publish_date
    
    def save(self, commit=True):
        """
        Override save method to handle slug generation and publish_date setting
        """
        news = super(NewsForm, self).save(commit=False)
        
        # Set slug if not already set
        if not news.slug:
            news.slug = self.clean_slug()
        
        # Set publish_date for published articles if not provided
        if news.status == 'published' and not news.publish_date:
            news.publish_date = timezone.now()
        
        if commit:
            news.save()
            # Save tags - needed because of ManyToMany relationship
            self.save_m2m()
            
        return news


class CommentForm(forms.ModelForm):
    """
    Form for creating comments on news articles.
    """
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write your comment here...'
            }),
        }
    
    def clean_content(self):
        """
        Validate comment content - ensure it's not empty
        and doesn't contain only whitespace.
        """
        content = self.cleaned_data.get('content')
        if not content or content.strip() == '':
            raise forms.ValidationError("Comment content cannot be empty.")
        
        # Filter out potentially harmful content
        # Add basic filtering if needed
        
        return content


class NewsSearchForm(forms.Form):
    """
    Form for searching and filtering news articles.
    """
    q = forms.CharField(
        required=False,
        label='Search',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by keyword...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    sort = forms.ChoiceField(
        choices=[
            ('-publish_date', 'Newest First'),
            ('publish_date', 'Oldest First'),
            ('title', 'Title A-Z'),
            ('-title', 'Title Z-A'),
            ('-views', 'Most Viewed'),
        ],
        required=False,
        initial='-publish_date',
        widget=forms.Select(attrs={'class': 'form-control'})
    )