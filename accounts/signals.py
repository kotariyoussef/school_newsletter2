from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StudentProfile, StudentRequest

@receiver(post_save, sender=StudentRequest)
def create_student_profile(sender, instance, created=False, **kwargs):
    """Create a student profile when a student request is approved"""
    if not created and instance.approved:
        # Check if profile already exists
        if not hasattr(instance.user, 'studentprofile'):
            StudentProfile.objects.create(user=instance.user)