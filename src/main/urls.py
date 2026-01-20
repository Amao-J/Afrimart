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
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    

    path('cart/ajax/add/<int:product_id>/', views.ajax_add_to_cart, name='ajax_add_to_cart'),
    path('cart/ajax/count/', views.get_cart_count, name='get_cart_count'),
    
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
    

     path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
]