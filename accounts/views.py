from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import StudentRequest, StudentProfile
from .forms import StudentRequestForm, StudentProfileForm
from django.views.generic import ListView, DetailView


@login_required
def student_request_view(request):
    """View for submitting a student status request"""
    # Check if user already has a request or is already a student
    try:
        student_request = StudentRequest.objects.get(user=request.user)
        return redirect('accounts:student_request_status')
    except StudentRequest.DoesNotExist:
        pass
    
    # Check if already has a profile (is already a student)
    try:
        student_profile = StudentProfile.objects.get(user=request.user)
        messages.info(request, "You are already a student.")
        return redirect('accounts:student_profile')
    except StudentProfile.DoesNotExist:
        pass
    
    if request.method == 'POST':
        form = StudentRequestForm(request.POST)
        if form.is_valid():
            student_request = form.save(commit=False)
            student_request.user = request.user
            student_request.save()
            messages.success(request, "Your student status request has been submitted!")
            return redirect('accounts:student_request_status')
    else:
        form = StudentRequestForm()
    
    return render(request, 'accounts/student_request_form.html', {'form': form})

@login_required
def student_request_status(request):
    """View for checking student request status"""
    try:
        student_request = StudentRequest.objects.get(user=request.user)
        return render(request, 'accounts/student_request_status.html', 
                      {'student_request': student_request})
    except StudentRequest.DoesNotExist:
        messages.warning(request, "You don't have an active student request.")
        return redirect('accounts:student_request')

@login_required
def student_profile_view(request):
    """View for viewing student profile"""
    try:
        profile = StudentProfile.objects.get(user=request.user)
        return render(request, 'accounts/student_profile.html', {'profile': profile})
    except StudentProfile.DoesNotExist:
        try:
            student_request = StudentRequest.objects.get(user=request.user)
            if student_request.approved:
                # Create profile if approved but no profile exists yet
                profile = StudentProfile.objects.create(user=request.user)
                messages.success(request, "Your profile has been created! Please complete your details.")
                return redirect('accounts:edit_student_profile')
            else:
                return redirect('accounts:student_request_status')
        except StudentRequest.DoesNotExist:
            messages.warning(request, "You need to request student status first.")
            return redirect('accounts:student_request')

@login_required
def edit_student_profile(request):
    """View for editing student profile"""
    try:
        profile = StudentProfile.objects.get(user=request.user)
    except StudentProfile.DoesNotExist:
        try:
            student_request = StudentRequest.objects.get(user=request.user, approved=True)
            # Create profile if approved but doesn't exist
            profile = StudentProfile.objects.create(user=request.user)
        except StudentRequest.DoesNotExist:
            messages.warning(request, "You need to be an approved student to edit your profile.")
            return redirect('accounts:student_request')
    
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            if "save_and_contine" in request.POST:
                messages.success(request, "Your profile has been saved! You can Continue!")
                return redirect('accounts:edit_student_profile')
            else:
                messages.success(request, "Your profile has been updated!")
                return redirect('accounts:student_profile')
    else:
        form = StudentProfileForm(instance=profile)
    
    return render(request, 'accounts/edit_student_profile.html', {'form': form,
            "last_name": request.user.first_name,
            "first_name": request.user.last_name,})

class ProfileListView(ListView):
    model = StudentProfile
    template_name = 'accounts/profile_list.html'
    context_object_name = 'profiles'

class ProfileDetailView(DetailView):
    model = StudentProfile
    template_name = 'accounts/profile_detail.html'
    context_object_name = 'profile'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
