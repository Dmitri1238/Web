from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('course-video/<str:course_name>/', views.course_video, name='course_video'),
    path('save_registration/', views.save_registration, name='save_registration'),
    path('get_registrations/', views.get_registrations, name='get_registrations'),
    path('delete_registration/<int:reg_id>/', views.delete_registration, name='delete_registration'),
    path('courses/', views.courses, name='courses'),
    path('books/delete/<int:pk>/', views.delete_book, name='delete_book'),
    path('comment/delete/<int:pk>/', views.delete_comment, name='delete_comment'),
    path('books/<int:pk>/', views.book_detail, name='book_detail'),
    path('books/<int:book_id>/comment/', views.add_comment_view, name='add_comment'),
    path('api/book/<int:book_id>/delete_rating/', views.delete_rating, name='delete_rating'),
    path('api/book/<int:book_id>/rate/', views.rate_book, name='rate_book'),
    path('api/book/<int:book_id>/average/', views.get_average_rating, name='get_average_rating'),
    path('catalog/', views.catalog_view, name='catalog'),
    path('catalog/<slug:category>/', views.category_view, name='category'),
    path('add_to_cart/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/remove/<int:book_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('about/', views.about, name='about'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)