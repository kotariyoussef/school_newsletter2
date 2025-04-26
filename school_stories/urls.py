from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from ckeditor_uploader import views as ckeditor_views
from django.views.decorators.cache import never_cache
from accounts.views import ProfileListView, ProfileDetailView
from news.views import home_view, ContactView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('news/', include('news.urls')),
    path('contact/', ContactView.as_view(), name='contact'),
    path('ckeditor/upload/', login_required(ckeditor_views.upload), name='ckeditor_upload'),
    path('ckeditor/browse/', never_cache(login_required(ckeditor_views.browse)), name='ckeditor_browse'),
    path('profiles/', ProfileListView.as_view(), name='profile_list'),
    path('<slug:slug>/', ProfileDetailView.as_view(), name='profile_detail'),
    path('', home_view, name='home'),
]


urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
