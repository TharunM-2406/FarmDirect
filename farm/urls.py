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
    path('product/<int:product_id>/',
         views.ProductDetailsView, name='product_details'),

    # Cart and Checkout URLs
    path('add-to-cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('update-cart/', views.update_cart, name='update_cart'),
    path('cart-count/', views.cart_count, name='cart_count'),
    path('create-checkout-session/', views.create_checkout_session,
         name='create_checkout_session'),

    # Payment Success and Cancel URLs
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),

    # Orders and Order Details
    path('orders/', views.orders_detail_view, name='orders_detail_view'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),
    path('delivery/signup/', views.delivery_person_signup,
         name='delivery_person_signup'),
    path('delivery/login/', views.delivery_person_login,
         name='delivery_person_login'),
    path('delivery/logout/', views.delivery_person_logout,
         name='delivery_person_logout'),
    path('delivery/dashboard/', views.delivery_dashboard,
         name='delivery_dashboard'),
    path('delivery/chat/<int:order_id>/', views.chat_view, name='chat_view'),
    path('delivery/mark-delivered/<int:order_id>/',
         views.mark_order_delivered, name='mark_order_delivered'),
    path('delivery/orders/', views.delivery_view_orders,
         name='delivery_view_orders'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
