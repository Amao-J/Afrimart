# escrow/urls.py
from django.urls import path
from . import views

app_name = 'escrow'

urlpatterns = [
    
    path('', views.escrow_dashboard, name='dashboard'),
    path('history/', views.escrow_history, name='history'),
    path('help/', views.escrow_help, name='help'),
    
    # Transaction management
    path('initiate/<int:order_id>/', views.initiate_escrow, name='initiate'),
    path('payment/<int:escrow_id>/', views.process_escrow_payment, name='payment'),
    path('callback/', views.flutterwave_callback, name='flutterwave_callback'),
    path('detail/<int:escrow_id>/', views.escrow_detail, name='detail'),
     path('transaction/<int:escrow_id>/', views.escrow_transaction_detail, name='escrow_transaction_detail'),
     path('transaction/<int:escrow_id>/', views.escrow_transaction_detail, name='transaction_detail'),
    # Seller actions
    path('<int:escrow_id>/ship/', views.mark_as_shipped, name='mark_shipped'),
    
    # Buyer actions
    path('<int:escrow_id>/confirm-delivery/', views.confirm_delivery, name='confirm_delivery'),
    path('<int:escrow_id>/release/', views.release_funds, name='release_funds'),
    
    # Dispute management
    path('<int:escrow_id>/dispute/', views.raise_dispute, name='raise_dispute'),
    path('dispute/<int:dispute_id>/', views.dispute_detail, name='dispute_detail'),
]