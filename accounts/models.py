from django.db import models
from django.contrib.auth.models import User
from ckeditor_uploader.fields import RichTextUploadingField
from django.utils.text import slugify

class StudentRequest(models.Model):
    """Model for student status requests"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    reason = models.TextField(help_text="Why do you want to be a student on this platform?")
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    
    def _str_(self):
        return f"{self.user.username}'s student request"

class StudentProfile(models.Model):
    """Student profile model that extends the User model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = RichTextUploadingField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip()
    
    def _str_(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.full_name or self.user.username)
            self.slug = slug
        super().save(*args, **kwargs)