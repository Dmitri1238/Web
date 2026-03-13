from django.contrib import admin
from main.models import Book
from main.models import UserProfile

admin.site.register(Book)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'avatar')  # показывать поля
    search_fields = ('user__username',)
    list_filter = ('status',)