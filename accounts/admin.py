from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import StudentProfile, StudentRequest

class StudentRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'approved')
    list_filter = ('approved',)
    search_fields = ('user_username', 'user_email')
    actions = ['approve_requests']
    
    def approve_requests(self, request, queryset):
        for student_request in queryset:
            student_request.approved = True
            student_request.save()
        self.message_user(request, f"{queryset.count()} student request(s) have been approved.")
    
    approve_requests.short_description = "Approve selected student requests"

class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user_username', 'user_email',)

admin.site.register(StudentRequest, StudentRequestAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
