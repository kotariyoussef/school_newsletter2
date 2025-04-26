from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('student-request/', views.student_request_view, name='student_request'),
    path('student-profile/', views.student_profile_view, name='student_profile'),
    path('student-profile/edit/', views.edit_student_profile, name='edit_student_profile'),
    path('student-request/status/', views.student_request_status, name='student_request_status'),
]