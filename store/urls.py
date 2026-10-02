from django.urls import path
from . import views
from store.admin import public_admin_site

urlpatterns = [
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('register/', views.register, name='register'),
    path('login/', views.EmailLoginView.as_view(), name='login'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('contact/', views.contact, name='contact'),
    path("admin/", public_admin_site.urls),
    

    # Cart
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-item/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_view, name='cart'),

    # Payment
    path('checkout/', views.checkout, name='checkout'),

    
]
