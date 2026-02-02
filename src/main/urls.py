# main/urls.py - Add these URLs to your existing urls.py

from django.urls import path
from . import views
from . import auth

urlpatterns = [

    path('register/', auth.register_view, name='register'),
    path('login/', auth.login_view, name='login'),
    path('logout/', auth.logout_view, name='logout'),
    path('profile/', auth.profile_view, name='profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
   
    path('cart/', views.cart_view, name='cart'),
    
    path('cart/', views.cart_view, name='view_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart_view, name='update_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart_view, name='clear_cart'),
    

    path('cart/ajax/add/<int:product_id>/', views.ajax_add_to_cart, name='ajax_add_to_cart'),
    path('cart/ajax/count/', views.get_cart_count, name='get_cart_count'),
    path('wallet/', views.wallet_view, name='wallet'),
    
    path('set-currency/', views.set_currency, name='set_currency'),
    path('currency-rates/', views.get_currency_rates, name='get_currency_rates'),
    path('checkout/', views.checkout, name='checkout'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    
 
    path('payment/initiate/<int:order_id>/', views.initiate_normal_payment, name='initiate_normal_payment'),
    path('payment/<int:order_id>/', views.process_normal_payment, name='process_normal_payment'),
    path('payment/callback/', views.normal_payment_callback, name='normal_payment_callback'),
    path('payment/history/', views.payment_history, name='payment_history'),
    path('payment/<int:payment_id>/detail/', views.payment_detail, name='payment_detail'),
    
    # Webhook
    path('payment/webhook/', views.verify_payment_webhook, name='payment_webhook'),
    

    # Seller URLs
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/pending-approval/', auth.seller_pending_approval, name='seller_pending_approval'),
    path('seller/products/', views.seller_products, name='seller_products'),
    path('seller/product/add/', views.add_product, name='add_product'),
    path('seller/product/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('seller/product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('seller/product/<int:product_id>/upload-images/', views.upload_product_images, name='upload_product_images'),
    path('seller/image/<int:image_id>/delete/', views.delete_product_image, name='delete_product_image'),
    path('seller/image/<int:image_id>/set-primary/', views.set_primary_image, name='set_primary_image'),
    path('seller/orders/', views.seller_orders, name='seller_orders'),
    path('seller/order/<int:order_id>/', views.seller_order_detail, name='seller_order_detail'),

     path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
]