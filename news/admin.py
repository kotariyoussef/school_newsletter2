from django.contrib import admin
from .models import News, Category, Comment

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('user', 'content', 'created_at')
    can_delete = True

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'category', 'publish_date', 'is_featured', 'views')
    list_filter = ('status', 'created_at', 'publish_date', 'category', 'is_featured')
    search_fields = ('title', 'content', 'summary')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)
    date_hierarchy = 'publish_date'
    ordering = ('-publish_date',)
    inlines = [CommentInline]
    
    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser and not obj.author == request.user.userprofile:
            return ('author', 'status', 'is_featured')
        return super().get_readonly_fields(request, obj)
    
    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.author:
            obj.author = request.user.userprofile
        super().save_model(request, obj, form, change)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'news', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('user__user__username', 'content', 'news__title')
    actions = ['approve_comments']
    
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
    approve_comments.short_description = "Approve selected comments"