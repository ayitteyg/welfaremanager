from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    path('auth/signup/', views.signup, name='signup'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/profile/', views.profile_view, name='profile'),
    
    #manage church contact / info
    path('church-contact/', views.update_church_contact, name='church-contact'),
    path('church-info/', views.church_info, name='church-info'),
    
     # Yearly Dues Management (Admin only)
    path('yearly-dues/', views.YearlyDuesListCreateView.as_view(), name='yearly-dues-list'),
    path('yearly-dues/<int:pk>/', views.YearlyDuesDetailView.as_view(), name='yearly-dues-detail'),
     
    # Members
    path('members/', views.MemberListCreateView.as_view(), name='member-list'),
    path('members/<int:pk>/', views.MemberDetailView.as_view(), name='member-detail'),
    path('member-payment-history/', views.member_payment_history, name='member-payment-history'), 
    
    
    path('member-roles/', views.user_roles_list, name='user-roles-list'),
    path('member-roles/<int:user_id>/update/', views.update_user_roles, name='update-user-roles'),
    
    # Receipts
    path('receipts/', views.ReceiptListCreateView.as_view(), name='receipt-list'),
    path('receipts/<int:pk>/', views.ReceiptDetailView.as_view(), name='receipt-detail'),
    
    # Payments
    path('payments/', views.PaymentListCreateView.as_view(), name='payment-list'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    
    
    # Events
    path('events/', views.EventListCreateView.as_view(), name='event-list'),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event-detail'),
    
    
    #member dashboard path
    path('reports-member-dues/', views.member_dues_report, name='member-dues-report'),
    path('reports-transport-levies/', views.transport_levies_report, name='transport-levies-report'),
    path('events-upcoming-list/', views.events_list, name='events-list'),
    path('reports-outstanding-amounts/', views.outstanding_amounts_report, name='outstanding-amounts-report'),
    
    #main dashboard
    # Dashboard paths
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    path('dashboard/recent-activity/', views.dashboard_recent_activity, name='dashboard-recent-activity'),
    path('membership/insights/', views.membership_insights, name='membership-insights'),
    path('receipts/insights/', views.receipts_insights, name='receipts-insights'),
    path('payments/insights/', views.payments_insights, name='payments-insights'),
    path('events/insights/', views.events_insights, name='events-insights'),
]