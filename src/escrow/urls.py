# escrow/urls.py
from django.urls import path
from . import views

app_name = 'escrow'

urlpatterns = [
    # Escrow initiation and payment
    path('initiate/<int:order_id>/', views.initiate_escrow, name='initiate'),
    path('<int:escrow_id>/', views.escrow_detail, name='detail'),
    path('<int:escrow_id>/payment/', views.process_escrow_payment, name='payment'),
    path('callback/', views.flutterwave_callback, name='callback'),
    
    # Seller actions
    path('<int:escrow_id>/ship/', views.mark_as_shipped, name='ship'),
    
    # Buyer actions
    path('<int:escrow_id>/confirm/', views.confirm_delivery, name='confirm'),
    path('<int:escrow_id>/release/', views.release_funds, name='release'),
    
    # Disputes
    path('<int:escrow_id>/dispute/', views.raise_dispute, name='dispute'),
    path('dispute/<int:dispute_id>/', views.dispute_detail, name='dispute_detail'),
]