# forms.py
from django import forms
from news.models import News, Category
from django.utils.text import slugify
from taggit.forms import TagWidget
from ckeditor_uploader.widgets import CKEditorUploadingWidget

class NewsForm(forms.ModelForm):
    # Override the tags field to use TagWidget
    tags = forms.CharField(
        required=False,
        widget=TagWidget(attrs={'class': 'form-control', 'data-role': 'tagsinput'}),
        help_text="Enter tags separated by commas"
    )
    
    # Add category as a ModelChoiceField to customize the queryset if needed
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select Category",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Use CKEditor for content
    content = forms.CharField(widget=CKEditorUploadingWidget())
    
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
        fields = ['title', 'category', 'featured_image', 'summary', 'content', 
                  'is_featured', 'status', 'tags']
        widgets = {
            'summary': forms.Textarea(attrs={'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'featured_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if self.instance.pk is None:  # If creating new post
            slug = slugify(title)
            if News.objects.filter(slug=slug).exists():
                raise forms.ValidationError('A post with this title already exists. Please choose a different title.')
        return title

