from django.contrib import admin
from main.models import Book
from main.models import UserProfile
from main.models import Category

admin.site.register(Book)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'avatar')  # показывать поля
    search_fields = ('user__username',)
    list_filter = ('status',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {"slug": ("name",)}