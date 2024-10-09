from django.urls import path
from . import views
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('', views.home, name='home'),
    path("admin/", admin.site.urls, name='admin'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('farmer_signup/', views.farmer_signup, name='farmer_signup'),
    path('farmer_login/', views.farmer_login, name='farmer_login'),
    path('farmer_logout/', views.farmer_logout, name='farmer_logout'),
    path('dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('add_product/', views.add_product, name='add_product'),
    path('edit_product/<int:product_id>/',
         views.edit_product, name='edit_product'),
    path('delete_product/<int:product_id>/',
         views.delete_product, name='delete_product'),
    path('view_orders/', views.view_orders, name='view_orders'),
    path('view_products/', views.view_products, name='view_products'),
    path('catalog/', views.ProductCatalogView, name='product_catalog'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('add-to-cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('update-cart/', views.update_cart, name='update_cart'),
    path('cart-count/', views.cart_count, name='cart_count'),
    path('create-payment-intent/', views.create_checkout_session,
         name='create_checkout_session'),
    path('payment/success/', views.payment_success, name='success'),
    path('payment/cancel/', views.payment_cancel, name='cancel'),
    path('products/', views.products_detail_view, name='products_detail_view'),
    path('orders/', views.orders_detail_view, name='orders_detail_view'),
    path('product/<int:product_id>/',
         views.ProductDetailsView, name='product_details'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)