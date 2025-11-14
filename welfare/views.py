from rest_framework import status
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Sum, Count, Q

from .serializers import *
from .models import *

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        user_data = UserSerializer(user).data
        
        return Response({
            'message': 'User registered successfully',
            'user': user_data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Adjust permissions as needed
def user_roles_list(request):
    """
    Get all users with optional search
    """
    try:
        search_term = request.GET.get('search', '').strip()
        
        # Start with all users
        users = CustomUser.objects.all().select_related('church')
        
        # Apply search filter if provided
        if search_term:
            users = users.filter(
                Q(name__icontains=search_term) |
                Q(phone_number__icontains=search_term)
            )
        
        serializer = UserSerializer(users, many=True)
        return Response({
            'users': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'error': 'Failed to fetch users', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])  # Adjust permissions as needed
def update_user_roles(request, user_id):
    """
    Update user roles
    """
    try:
        # Get the user to update
        user = CustomUser.objects.get(id=user_id)
        
        # Extract role data from request
        is_member = request.data.get('is_member')
        is_welfare_admin = request.data.get('is_welfare_admin')
        is_church_admin = request.data.get('is_church_admin')
        
        # Prepare update data
        update_data = {}
        
        if is_member is not None:
            update_data['is_member'] = is_member
        if is_welfare_admin is not None:
            update_data['is_welfare_admin'] = is_welfare_admin
        if is_church_admin is not None:
            update_data['is_church_admin'] = is_church_admin
        
        # Check if update would result in no roles
        if update_data:
            # Create a copy of current values with updates applied
            test_member = update_data.get('is_member', user.is_member)
            test_welfare = update_data.get('is_welfare_admin', user.is_welfare_admin)
            test_church = update_data.get('is_church_admin', user.is_church_admin)
            
            # Ensure at least one role is true
            if not any([test_member, test_welfare, test_church]):
                return Response(
                    {'error': 'User must have at least one role'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Update the user
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.save()
        
        # Return updated user data
        serializer = UserSerializer(user)
        return Response({
            'user': serializer.data,
            'message': 'User roles updated successfully'
        })
        
    except CustomUser.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': 'Failed to update user roles', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )





@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Generate tokens directly without password authentication
        refresh = RefreshToken.for_user(user)
        
        user_data = UserSerializer(user).data
        
        return Response({
            'message': 'Login successful',
            'user': user_data,
            'access': str(refresh.access_token),  # Move to root level
            'refresh': str(refresh),  # Move to root level
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    user_data = UserSerializer(request.user).data
    return Response({'user': user_data})


# Base permission class
class ChurchBasedPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Users can only access objects from their own church
        return obj.church == request.user.church



# MemberListCreateView
class MemberListCreateView(generics.ListCreateAPIView):
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Member.objects.filter(church=self.request.user.church)

    def perform_create(self, serializer):
        serializer.save(church=self.request.user.church)


# MemberDetailView
class MemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated, ChurchBasedPermission]

    def get_queryset(self):
        return Member.objects.filter(church=self.request.user.church)







# ReceiptListCreateView
class ReceiptListCreateView(generics.ListCreateAPIView):
    serializer_class = ReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Receipt.objects.filter(member__church=self.request.user.church)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        
# ReceiptDetailView
class ReceiptDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Receipt.objects.filter(member__church=self.request.user.church)




# Payment Views
class PaymentListCreateView(generics.ListCreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(church=self.request.user.church)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, church=self.request.user.church)

class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, ChurchBasedPermission]

    def get_queryset(self):
        return Payment.objects.filter(church=self.request.user.church)




# Event Views
class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Event.objects.filter(church=self.request.user.church)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, church=self.request.user.church)

class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated, ChurchBasedPermission]

    def get_queryset(self):
        return Event.objects.filter(church=self.request.user.church)





# views.py
class YearlyDuesListCreateView(generics.ListCreateAPIView):
    serializer_class = YearlyDuesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return YearlyDues.objects.filter(church=self.request.user.church)

    def perform_create(self, serializer):
        # Only welfare admins can create yearly dues
        if not self.request.user.is_welfare_admin:
            raise PermissionDenied("Only welfare admins can set yearly dues")
        serializer.save(created_by=self.request.user, church=self.request.user.church)


class YearlyDuesDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = YearlyDuesSerializer
    permission_classes = [permissions.IsAuthenticated, ChurchBasedPermission]

    def get_queryset(self):
        return YearlyDues.objects.filter(church=self.request.user.church)

    def perform_update(self, serializer):
        # Only welfare admins can update yearly dues
        if not self.request.user.is_welfare_admin:
            raise PermissionDenied("Only welfare admins can update yearly dues")
        serializer.save()






# member_dues_report
@api_view(['GET'])
def member_dues_report(request):
    """
    Returns member dues report for the logged-in user only
    """
    user = request.user
    church = user.church
    current_year = timezone.now().year
    
    # Get the member record for the logged-in user
    members = Member.objects.all()
    print(members)
    try:
        member = Member.objects.get(user=user, church=church)
    except Member.DoesNotExist:
        return Response({"error": "Member profile not found"}, status=404)
    
    # Check if member is active
    is_active_member = member.status == 'active'
    
    # Calculate totals using YearlyDues
    all_yearly_dues = YearlyDues.objects.filter(church=church)
    yearly_dues_dict = {yd.year: yd.monthly_amount for yd in all_yearly_dues}
    
    # Get all years we have receipts for THIS USER
    receipt_years = Receipt.objects.filter(
        member=member,  # Filter by specific member
        receipt_type='monthly_dues'
    ).values_list('year', flat=True).distinct()
    
    print(receipt_years)
    
    # Calculate total expected and total paid FOR THIS USER
    total_expected = 0
    total_paid = 0
    payment_history = []
    
    # Process each year we have data for
    years_to_show = sorted(set(range(current_year - 3, current_year + 1)) | set(receipt_years))
    
    
    print(f"Current year: {current_year}")
    print(f"Years to show: {years_to_show}")
    print(f"Yearly dues available: {yearly_dues_dict}")
    
    for year in sorted(years_to_show, reverse=True):
        # Get monthly due amount for this year
        monthly_amount = yearly_dues_dict.get(year)
        if monthly_amount is None:
            monthly_amount = 0 #yearly_dues_dict.get(current_year, 0)
        
        # Calculate expected for this year FOR THIS USER ONLY
        year_expected = 12 * monthly_amount if is_active_member else 0
        print(f"Year: {year}, Monthly: {monthly_amount}, Expected: {year_expected}")
        
        # Get actual paid for this year FOR THIS USER
        year_receipts = Receipt.objects.filter(
            member=member,  # Filter by specific member
            receipt_type='monthly_dues',
            year=year
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate progress
        year_progress = (year_receipts / year_expected * 100) if year_expected > 0 else 0
        
        # Add to payment history (only if we have data)
        if year_receipts > 0 or year_expected > 0:
            payment_history.append({
                'year': year,
                'amountPaid': float(year_receipts),
                'progress': round(year_progress, 1)
            })
        
        # Add to totals
        total_expected += year_expected
        total_paid += year_receipts
    
    # Calculate overall progress
    overall_progress = (total_paid / total_expected * 100) if total_expected > 0 else 0
    
    # Get current year specific data FOR THIS USER
    current_monthly_amount = yearly_dues_dict.get(current_year, 10)
    current_year_expected = 12 * current_monthly_amount if is_active_member else 0
    current_year_receipts = Receipt.objects.filter(
        member=member,  # Filter by specific member
        receipt_type='monthly_dues',
        year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    current_year_progress = (current_year_receipts / current_year_expected * 100) if current_year_expected > 0 else 0
    
    response_data = {
        'totalDuesExpected': float(total_expected),
        'totalPaid': float(total_paid),
        'overallProgress': round(overall_progress, 1),
        
        'currentYear': current_year,
        'currentYearExpected': float(current_year_expected),
        'currentYearPaid': float(current_year_receipts),
        'currentYearProgress': round(current_year_progress, 1),
        
        'paymentHistory': payment_history[:4],
        'memberStatus': member.status
    }
    
    return Response(response_data)



@api_view(['GET'])
def transport_levies_report(request):
    """
    Returns transport levies report for the CURRENT MEMBER in the exact format expected by frontend
    """
    current_member = request.user.member_profile  # Get the member profile of current user
    church = request.user.church
    current_year = timezone.now().year
    
    # Calculate transport levies from receipts FOR CURRENT MEMBER
    total_transport_receipts = Receipt.objects.filter(
        member=current_member,
        receipt_type='transport_levy'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate expected transport levies from events FOR CURRENT MEMBER
    total_events_levy = Event.objects.filter(
        member=current_member,
        is_levy_paid=False  # Only count unpaid levies as expected
    ).aggregate(total=Sum('levy_amount'))['total'] or 0
    
    total_expected = total_events_levy
    total_paid = total_transport_receipts
    
    # Current year calculations FOR CURRENT MEMBER
    current_year_receipts = Receipt.objects.filter(
        member=current_member,
        receipt_type='transport_levy',
        year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    current_year_expected = Event.objects.filter(
        member=current_member,
        is_levy_paid=False,
        event_date__year=current_year
    ).aggregate(total=Sum('levy_amount'))['total'] or 0
    
    # Calculate progress percentages
    overall_progress = (total_paid / total_expected * 100) if total_expected > 0 else 0
    current_year_progress = (current_year_receipts / current_year_expected * 100) if current_year_expected > 0 else 0
    
    # Member contributions (transport levy receipts FOR CURRENT MEMBER)
    member_contributions = []
    transport_receipts = Receipt.objects.filter(
        member=current_member,
        receipt_type='transport_levy'
    ).select_related('member').order_by('-date')[:10]  # Last 10 contributions
    
    for receipt in transport_receipts:
        # Try to find related event for this receipt
        related_event = Event.objects.filter(
            member=current_member,
            event_date__year=receipt.year
        ).first()
        
        purpose = "Transport levy"
        if related_event:
            purpose = f"{related_event.get_event_type_display()} - {related_event.description}"
        
        member_contributions.append({
            'memberName': receipt.member.full_name,
            'amountPaid': float(receipt.amount),
            'progress': 100,  # Since they've paid, progress is 100%
            'date': receipt.date.strftime('%b %d, %Y'),
            'purpose': purpose
        })
    
    response_data = {
        'totalTransportExpected': float(total_expected),
        'totalPaid': float(total_paid),
        'overallProgress': round(overall_progress, 1),
        
        'currentYear': current_year,
        'currentYearExpected': float(current_year_expected),
        'currentYearPaid': float(current_year_receipts),
        'currentYearProgress': round(current_year_progress, 1),
        
        'memberContributions': member_contributions
    }
    
    return Response(response_data)

# events_list
@api_view(['GET'])
def events_list(request):
    """
    Returns events in the format expected by frontend
    """
    church = request.user.church
    today = timezone.now().date()
    
    events = Event.objects.filter(church=church).select_related('member', 'created_by').order_by('-event_date')
    
    events_data = []
    for event in events:
        events_data.append({
            'id': event.id,
            'event_type': event.event_type,
            'event_type_display': event.get_event_type_display(),
            'member': {
                'id': event.member.id,
                'full_name': event.member.full_name
            },
            'event_date': event.event_date,
            'venue': event.venue,
            'description': event.description,
            'levy_amount': float(event.levy_amount),
            'is_levy_paid': event.is_levy_paid,
            'created_by_name': event.created_by.name
        })
    
    return Response(events_data)


@api_view(['GET'])
def outstanding_amounts_report(request):
    """
    Returns outstanding amounts and recent payments for CURRENT MEMBER in the exact format expected by frontend
    """
    current_member = request.user.member_profile
    current_year = timezone.now().year
    
    # Calculate outstanding dues per year FOR CURRENT MEMBER
    outstanding_dues = {}
    years_with_dues = Receipt.objects.filter(
        member=current_member,
        receipt_type='monthly_dues'
    ).values_list('year', flat=True).distinct()
    
    for year in sorted(years_with_dues, reverse=True)[:2]:  # Last 2 years
        # Get expected dues for this year FOR CURRENT MEMBER
        yearly_dues = YearlyDues.objects.filter(church=request.user.church, year=year).first()
        if yearly_dues:
            # For individual member: 12 months × monthly amount
            expected_amount = 12 * yearly_dues.monthly_amount
        else:
            expected_amount = 0
        
        # Get actual paid for this year FOR CURRENT MEMBER
        paid_amount = Receipt.objects.filter(
            member=current_member,
            receipt_type='monthly_dues',
            year=year
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        outstanding = max(0, expected_amount - paid_amount)
        if outstanding > 0:
            outstanding_dues[str(year)] = float(outstanding)
    
    # Calculate outstanding transport levies per year FOR CURRENT MEMBER
    outstanding_transport = {}
    for year in range(current_year - 1, current_year + 1):  # Current and previous year
        unpaid_levies = Event.objects.filter(
            member=current_member,
            is_levy_paid=False,
            event_date__year=year
        ).aggregate(total=Sum('levy_amount'))['total'] or 0
        
        if unpaid_levies > 0:
            outstanding_transport[str(year)] = float(unpaid_levies)
    
    # Get recent payments FOR CURRENT MEMBER (last 10 receipts)
    recent_receipts = Receipt.objects.filter(
        member=current_member
    ).select_related('member').order_by('-date')[:10]
    
    recent_payments = []
    for receipt in recent_receipts:
        receipt_type_display = 'Dues' if receipt.receipt_type == 'monthly_dues' else 'Transport Levy'
        
        recent_payments.append({
            'id': receipt.id,
            'type': receipt_type_display,
            'amount': float(receipt.amount),
            'date': receipt.date.strftime('%Y-%m-%d'),
            'year': str(receipt.year),
            'details': receipt.details or f"{receipt_type_display} payment",
            'receiptNumber': receipt.receipt_number
        })
    
    response_data = {
        'outstandingDues': outstanding_dues,
        'outstandingTransport': outstanding_transport,
        'recentPayments': recent_payments
    }
    
    return Response(response_data)



@api_view(['GET'])
def member_payment_history(request):
    """
    Returns payment history for the current member
    """
    try:
        current_member = request.user.member_profile
    except Member.DoesNotExist:
        return Response(
            {'error': 'Member profile not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get all receipts for the current member
    receipts = Receipt.objects.filter(
        member=current_member
    ).select_related('member').order_by('-date')
    
    payment_history = []
    for receipt in receipts:
        payment_history.append({
            'id': receipt.id,
            'receipt_number': receipt.receipt_number,
            'receipt_type': receipt.receipt_type,
            'date': receipt.date,
            'amount': float(receipt.amount),
            'year': receipt.year,
            'details': receipt.details or '',
            'created_at': receipt.created_at
        })
    
    return Response(payment_history)



@api_view(['GET'])
def church_info(request):
    """
    Get church information for the current user
    """
    church = request.user.church
    serializer = ChurchSerializer(church)
    return Response(serializer.data)


@api_view(['PATCH'])
def update_church_contact(request):
    """
    Update church contact information (email, welfare_momo, church_momo)
    """
    church = request.user.church
    
    # Only allow updating specific fields
    allowed_fields = ['email', 'welfare_momo', 'church_momo']
    update_data = {field: request.data.get(field) for field in allowed_fields if field in request.data}
    
    serializer = ChurchSerializer(church, data=update_data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Contact information updated successfully',
            'church': serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






@api_view(['GET'])
def dashboard_stats(request):
    """
    Returns dashboard statistics for the church welfare admin
    """
    church = request.user.church
    current_year = timezone.now().year
    current_month = timezone.now().month
    
    # Member statistics
    total_members = Member.objects.filter(church=church).count()
    active_members = Member.objects.filter(church=church, status='active').count()
    
    # Financial statistics - Total
    total_receipts = Receipt.objects.filter(
        member__church=church
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_payments = Payment.objects.filter(
        church=church
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Financial statistics - Current Month
    monthly_receipts = Receipt.objects.filter(
        member__church=church,
        date__year=current_year,
        date__month=current_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    monthly_payments = Payment.objects.filter(
        church=church,
        date__year=current_year,
        date__month=current_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Event statistics
    total_events = Event.objects.filter(church=church).count()
    upcoming_events = Event.objects.filter(
        church=church,
        event_date__gte=timezone.now().date()
    ).count()
    
    response_data = {
        'total_members': total_members,
        'active_members': active_members,
        'total_receipts': float(total_receipts),
        'monthly_receipts': float(monthly_receipts),
        'total_payments': float(total_payments),
        'monthly_payments': float(monthly_payments),
        'total_events': total_events,
        'upcoming_events': upcoming_events,
        'balance': float(total_receipts - total_payments)
    }
    
    return Response(response_data)


from django.utils import timezone
from datetime import timedelta

def get_time_since(dt):
    """
    Calculate relative time string (e.g., '2 hours ago', '3 days ago')
    """
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 0:
        if diff.days == 1:
            return '1 day ago'
        elif diff.days < 7:
            return f'{diff.days} days ago'
        elif diff.days < 30:
            weeks = diff.days // 7
            return f'{weeks} week{"s" if weeks > 1 else ""} ago'
        else:
            months = diff.days // 30
            return f'{months} month{"s" if months > 1 else ""} ago'
    else:
        seconds = diff.seconds
        if seconds < 60:
            return 'just now'
        elif seconds < 3600:
            minutes = seconds // 60
            return f'{minutes} minute{"s" if minutes > 1 else ""} ago'
        else:
            hours = seconds // 3600
            return f'{hours} hour{"s" if hours > 1 else ""} ago'

@api_view(['GET'])
def dashboard_recent_activity(request):
    """
    Returns recent activity for the dashboard
    """
    church = request.user.church
    recent_activity = []
    
    # Get recent receipts (last 5)
    recent_receipts = Receipt.objects.filter(
        member__church=church
    ).select_related('member').order_by('-created_at')[:5]
    
    for receipt in recent_receipts:
        recent_activity.append({
            'type': 'receipt',
            'description': f'{receipt.member.full_name} paid {receipt.get_receipt_type_display()}',
            'time': get_time_since(receipt.created_at),
            'timestamp': receipt.created_at
        })
    
    # Get recent events (last 5)
    recent_events = Event.objects.filter(
        church=church
    ).select_related('member').order_by('-created_at')[:5]
    
    for event in recent_events:
        recent_activity.append({
            'type': 'event',
            'description': f'New {event.get_event_type_display()} event for {event.member.full_name}',
            'time': get_time_since(event.created_at),
            'timestamp': event.created_at
        })
    
    # Get recent payments (last 5)
    recent_payments = Payment.objects.filter(
        church=church
    ).order_by('-created_at')[:5]
    
    for payment in recent_payments:
        recent_activity.append({
            'type': 'payment',
            'description': f'{payment.get_payment_type_display()} payment to {payment.payee_name}',
            'time': get_time_since(payment.created_at),
            'timestamp': payment.created_at
        })
    
    # Get recent member updates (last 5)
    recent_members = Member.objects.filter(
        church=church
    ).order_by('-updated_at')[:5]
    
    for member in recent_members:
        if member.updated_at != member.created_at:  # Only count updates, not creations
            recent_activity.append({
                'type': 'member',
                'description': f'{member.full_name} updated profile',
                'time': get_time_since(member.updated_at),
                'timestamp': member.updated_at
            })
    
    # Sort by timestamp and take top 10
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activity = recent_activity[:10]
    
    # Remove timestamp from response
    for activity in recent_activity:
        activity.pop('timestamp', None)
    
    return Response(recent_activity)




@api_view(['GET'])
def membership_insights(request):
    """
    Returns comprehensive membership insights and analytics
    """
    church = request.user.church
    current_year = timezone.now().year
    
    # Basic member counts
    total_members = Member.objects.filter(church=church).count()
    active_members = Member.objects.filter(church=church, status='active').count()
    
    # Gender breakdown
    male_count = Member.objects.filter(church=church, gender='male').count()
    female_count = Member.objects.filter(church=church, gender='female').count()
    
    # Status breakdown
    status_breakdown = []
    for status_value, status_label in Member.MEMBER_STATUS:
        count = Member.objects.filter(church=church, status=status_value).count()
        status_breakdown.append({
            'status': status_label,
            'count': count
        })
    
    # Calculate compliance rate (members who have paid current year dues)
    current_year_dues_paid = Receipt.objects.filter(
        member__church=church,
        receipt_type='monthly_dues',
        year=current_year
    ).values('member').distinct().count()
    
    compliance_rate = round((current_year_dues_paid / active_members * 100)) if active_members > 0 else 0
    
    # Regular contributors (members with at least 3 payments this year)
    regular_contributors = Receipt.objects.filter(
        member__church=church,
        receipt_type='monthly_dues',
        year=current_year
    ).values('member').annotate(payment_count=Count('id')).filter(payment_count__gte=3).count()
    
    # Outstanding dues calculation
    current_dues = YearlyDues.objects.filter(church=church, year=current_year).first()
    if current_dues:
        expected_per_member = 12 * current_dues.monthly_amount
    else:
        expected_per_member = 0
    
    # Calculate members with outstanding dues
    members_with_dues = []
    all_active_members = Member.objects.filter(church=church, status='active')
    
    for member in all_active_members:
        paid_amount = Receipt.objects.filter(
            member=member,
            receipt_type='monthly_dues',
            year=current_year
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        if paid_amount < expected_per_member:
            members_with_dues.append(member)
    
    members_with_outstanding_dues = len(members_with_dues)
    total_outstanding_amount = members_with_outstanding_dues * (expected_per_member - (paid_amount if paid_amount else 0))
    
    # Top contributors (based on total payments across all years)
    top_contributors_data = Receipt.objects.filter(
        member__church=church
    ).values(
        'member__id', 'member__full_name'
    ).annotate(
        total_amount=Sum('amount')
    ).order_by('-total_amount')[:5]
    
    top_contributors = []
    for contributor in top_contributors_data:
        top_contributors.append({
            'name': contributor['member__full_name'],
            'amount': float(contributor['total_amount'])
        })
    
    response_data = {
        'total_members': total_members,
        'active_members': active_members,
        'male_count': male_count,
        'female_count': female_count,
        'compliance_rate': compliance_rate,
        'regular_contributors': regular_contributors,
        'members_with_outstanding_dues': members_with_outstanding_dues,
        'total_outstanding_amount': float(total_outstanding_amount),
        'status_breakdown': status_breakdown,
        'top_contributors': top_contributors
    }
    
    return Response(response_data)







@api_view(['GET'])
def receipts_insights(request):
    """
    Returns comprehensive receipts insights and analytics
    """
    church = request.user.church
    current_year = timezone.now().year
    current_month = timezone.now().month
    
    # Get year from query params, default to current year
    year = request.GET.get('year', current_year)
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = current_year
    
    # Total receipts for the year
    year_receipts = Receipt.objects.filter(
        member__church=church,
        year=year
    )
    
    total_year_receipts = year_receipts.aggregate(total=Sum('amount'))['total'] or 0
    total_receipts_count = year_receipts.count()
    
    # Current month receipts
    current_month_receipts = Receipt.objects.filter(
        member__church=church,
        date__year=current_year,
        date__month=current_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Previous month for growth calculation
    previous_month = current_month - 1 if current_month > 1 else 12
    previous_month_year = current_year if current_month > 1 else current_year - 1
    
    previous_month_receipts = Receipt.objects.filter(
        member__church=church,
        date__year=previous_month_year,
        date__month=previous_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Monthly growth calculation
    monthly_growth = 0
    if previous_month_receipts > 0:
        monthly_growth = ((current_month_receipts - previous_month_receipts) / previous_month_receipts) * 100
    
    # Average receipt amount
    average_receipt_amount = total_year_receipts / total_receipts_count if total_receipts_count > 0 else 0
    
    # Type breakdown for the year
    monthly_dues_total = Receipt.objects.filter(
        member__church=church,
        receipt_type='monthly_dues',
        year=year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    transport_levy_total = Receipt.objects.filter(
        member__church=church,
        receipt_type='transport_levy',
        year=year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    other_types_total = Receipt.objects.filter(
        member__church=church,
        receipt_type__in=['donation', 'passbook', 'other'],
        year=year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Monthly trends for the year
    monthly_trends = []
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for month_num in range(1, 13):
        month_receipts = Receipt.objects.filter(
            member__church=church,
            date__year=year,
            date__month=month_num
        )
        
        month_total = month_receipts.aggregate(total=Sum('amount'))['total'] or 0
        month_dues = month_receipts.filter(receipt_type='monthly_dues').aggregate(total=Sum('amount'))['total'] or 0
        month_transport = month_receipts.filter(receipt_type='transport_levy').aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_trends.append({
            'month': months[month_num - 1],
            'total': float(month_total),
            'monthly_dues': float(month_dues),
            'transport_levy': float(month_transport)
        })
    
    # Monthly dues compliance rate
    active_members = Member.objects.filter(church=church, status='active').count()
    members_paid_dues = Receipt.objects.filter(
        member__church=church,
        receipt_type='monthly_dues',
        year=year
    ).values('member').distinct().count()
    
    print(members_paid_dues, active_members)
    
    monthly_dues_compliance = round((members_paid_dues / active_members * 100)) if active_members > 0 else 0
    monthly_dues_target = 85  # Default target
    
    # Transport levy efficiency (collected vs expected from events)
    total_events_levy = Event.objects.filter(
        church=church,
        event_type='funeral',
        event_date__year=year
    ).aggregate(total=Sum('levy_amount'))['total'] or 0
    
    
    print(transport_levy_total, total_events_levy)
    
    transport_levy_efficiency = round((transport_levy_total / total_events_levy * 100)) if total_events_levy > 0 else 0
    transport_levy_expected = 75  # Default expected rate
    
    # Top contributors for the year
    top_contributors_data = Receipt.objects.filter(
        member__church=church,
        year=year
    ).values(
        'member__id', 'member__full_name'
    ).annotate(
        total=Sum('amount'),
        monthly_dues=Sum('amount', filter=models.Q(receipt_type='monthly_dues')),
        transport_levy=Sum('amount', filter=models.Q(receipt_type='transport_levy'))
    ).order_by('-total')[:5]
    
    top_contributors = []
    for contributor in top_contributors_data:
        top_contributors.append({
            'name': contributor['member__full_name'],
            'total': float(contributor['total']),
            'monthly_dues': float(contributor['monthly_dues'] or 0),
            'transport_levy': float(contributor['transport_levy'] or 0)
        })
    
    response_data = {
        'total_year_receipts': float(total_year_receipts),
        'total_receipts_count': total_receipts_count,
        'current_month_total': float(current_month_receipts),
        'monthly_growth': round(monthly_growth, 1),
        'average_receipt_amount': round(float(average_receipt_amount), 2),
        
        'monthly_dues_total': float(monthly_dues_total),
        'transport_levy_total': float(transport_levy_total),
        'other_types_total': float(other_types_total),
        
        'monthly_trends': monthly_trends,
        
        'monthly_dues_compliance': monthly_dues_compliance,
        'monthly_dues_target': monthly_dues_target,
        'transport_levy_efficiency': transport_levy_efficiency,
        'transport_levy_expected': transport_levy_expected,
        
        'top_contributors': top_contributors
    }
    
    return Response(response_data)





@api_view(['GET'])
def payments_insights(request):
    """
    Returns comprehensive payments insights and financial health analytics
    """
    church = request.user.church
    current_year = timezone.now().year
    current_month = timezone.now().month
    
    # Get year from query params, default to current year
    year = request.GET.get('year', current_year)
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = current_year
    
    # Total payments for the year
    year_payments = Payment.objects.filter(
        church=church,
        date__year=year
    )
    
    total_year_payments = year_payments.aggregate(total=Sum('amount'))['total'] or 0
    total_payments_count = year_payments.count()
    
    # Current month payments
    current_month_payments = Payment.objects.filter(
        church=church,
        date__year=current_year,
        date__month=current_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Previous month for growth calculation
    previous_month = current_month - 1 if current_month > 1 else 12
    previous_month_year = current_year if current_month > 1 else current_year - 1
    
    previous_month_payments = Payment.objects.filter(
        church=church,
        date__year=previous_month_year,
        date__month=previous_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Monthly growth calculation (negative growth is good for payments - less spending)
    monthly_growth = 0
    if previous_month_payments > 0:
        monthly_growth = ((current_month_payments - previous_month_payments) / previous_month_payments) * 100
    
    # Average payment amount
    average_payment_amount = total_year_payments / total_payments_count if total_payments_count > 0 else 0
    
    # Payment type breakdown for the year
    member_benefits_total = Payment.objects.filter(
        church=church,
        payment_type='member_benefit',
        date__year=year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    operational_total = Payment.objects.filter(
        church=church,
        payment_type='operational_expense', 
        date__year=year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    event_expenses_total = Payment.objects.filter(
        church=church,
        payment_type='event_expense',
        date__year=year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    other_expenses_total = Payment.objects.filter(
        church=church,
        payment_type='other',
        date__year=year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Monthly trends for the year
    monthly_trends = []
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for month_num in range(1, 13):
        month_payments = Payment.objects.filter(
            church=church,
            date__year=year,
            date__month=month_num
        )
        
        month_total = month_payments.aggregate(total=Sum('amount'))['total'] or 0
        month_member_benefits = month_payments.filter(payment_type='member_benefit').aggregate(total=Sum('amount'))['total'] or 0
        month_operational = month_payments.filter(payment_type='operational_expense').aggregate(total=Sum('amount'))['total'] or 0
        month_event_expenses = month_payments.filter(payment_type='event_expense').aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_trends.append({
            'month': months[month_num - 1],
            'total': float(month_total),
            'member_benefits': float(month_member_benefits),
            'operational': float(month_operational),
            'event_expenses': float(month_event_expenses)
        })
    
    # Financial Health Metrics
    
    # Total receipts for the year (for financial health calculations)
    total_receipts = Receipt.objects.filter(
        member__church=church,
        year=year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Monthly surplus (current month receipts - current month payments)
    current_month_receipts = Receipt.objects.filter(
        member__church=church,
        date__year=current_year,
        date__month=current_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    monthly_surplus = current_month_receipts - current_month_payments
    
    # Spending ratio (payments ÷ receipts)
    spending_ratio = round((total_year_payments / total_receipts * 100)) if total_receipts > 0 else 0
    
    # Welfare ratio (member benefits ÷ total payments)
    welfare_ratio = round((member_benefits_total / total_year_payments * 100)) if total_year_payments > 0 else 0
    
    # Yearly balance (receipts - payments)
    yearly_balance = total_receipts - total_year_payments
    
    response_data = {
        # Financial Health
        'monthly_surplus': float(monthly_surplus),
        'spending_ratio': spending_ratio,
        'welfare_ratio': welfare_ratio,
        'total_receipts': float(total_receipts),
        'yearly_balance': float(yearly_balance),
        
        # Payments Overview
        'total_year_payments': float(total_year_payments),
        'total_payments_count': total_payments_count,
        'current_month_total': float(current_month_payments),
        'monthly_growth': round(monthly_growth, 1),
        'average_payment_amount': round(float(average_payment_amount), 2),
        
        # Payment Type Breakdown
        'member_benefits_total': float(member_benefits_total),
        'operational_total': float(operational_total),
        'event_expenses_total': float(event_expenses_total),
        'other_expenses_total': float(other_expenses_total),
        
        # Trends
        'monthly_trends': monthly_trends
    }
    
    return Response(response_data)




@api_view(['GET'])
def events_insights(request):
    """
    Returns comprehensive events insights and analytics
    """
    church = request.user.church
    current_year = timezone.now().year
    current_month = timezone.now().month
    
    # Get year from query params, default to current year
    year = request.GET.get('year', current_year)
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = current_year
    
    # Event volume
    total_events = Event.objects.filter(
        church=church,
        event_date__year=year
    ).count()
    
    current_month_events = Event.objects.filter(
        church=church,
        event_date__year=current_year,
        event_date__month=current_month
    ).count()
    
    # Event type distribution
    event_type_distribution = []
    for event_type, event_label in Event.EVENT_TYPES:
        count = Event.objects.filter(
            church=church,
            event_type=event_type,
            event_date__year=year
        ).count()
        event_type_distribution.append({
            'event_type': event_type,
            'count': count
        })
    
    # Financial impact
    events_with_levy = Event.objects.filter(
        church=church,
        event_date__year=year,
        levy_amount__gt=0
    ).count()
    
    total_levy_collected = Receipt.objects.filter(
        member__church=church,
        receipt_type='transport_levy',
        year=year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_levy_expected = Event.objects.filter(
        church=church,
        event_date__year=year
    ).aggregate(total=Sum('levy_amount'))['total'] or 0
    
    # Levy collection rate
    levy_collection_rate = round((total_levy_collected / total_levy_expected * 100)) if total_levy_expected > 0 else 0
    
    # Average levy amount
    average_levy_amount = total_levy_collected / events_with_levy if events_with_levy > 0 else 0
    
    # Cost recovery rate (levies collected vs total event costs)
    # This is a simplified calculation - you might want to track actual event costs separately
    total_event_payments = Payment.objects.filter(
        church=church,
        payment_type='event_expense',
        date__year=year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    cost_recovery_rate = round((total_levy_collected / total_event_payments * 100)) if total_event_payments > 0 else 0
    
    # Monthly trends
    monthly_trends = []
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for month_num in range(1, 13):
        month_events = Event.objects.filter(
            church=church,
            event_date__year=year,
            event_date__month=month_num
        )
        
        month_total_events = month_events.count()
        month_levy_collected = Receipt.objects.filter(
            member__church=church,
            receipt_type='transport_levy',
            date__year=year,
            date__month=month_num
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        month_levy_expected = month_events.aggregate(total=Sum('levy_amount'))['total'] or 0
        month_levy_rate = round((month_levy_collected / month_levy_expected * 100)) if month_levy_expected > 0 else 0
        
        monthly_trends.append({
            'month': months[month_num - 1],
            'total_events': month_total_events,
            'levy_collected': float(month_levy_collected),
            'levy_collection_rate': month_levy_rate
        })
    
    # Levy trend (current month vs previous month)
    previous_month = current_month - 1 if current_month > 1 else 12
    previous_month_year = current_year if current_month > 1 else current_year - 1
    
    current_month_levy = Receipt.objects.filter(
        member__church=church,
        receipt_type='transport_levy',
        date__year=current_year,
        date__month=current_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    previous_month_levy = Receipt.objects.filter(
        member__church=church,
        receipt_type='transport_levy',
        date__year=previous_month_year,
        date__month=previous_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    levy_trend = 0
    if previous_month_levy > 0:
        levy_trend = ((current_month_levy - previous_month_levy) / previous_month_levy) * 100
    
    # Performance targets
    levy_collection_target = 85  # Default target
    
    response_data = {
        # Event Volume
        'total_events': total_events,
        'current_month_events': current_month_events,
        
        # Event Type Distribution
        'event_type_distribution': event_type_distribution,
        
        # Financial Impact
        'total_levy_collected': float(total_levy_collected),
        'levy_collection_rate': levy_collection_rate,
        'average_levy_amount': round(float(average_levy_amount), 2),
        'events_with_levy': events_with_levy,
        'cost_recovery_rate': cost_recovery_rate,
        
        # Trends
        'monthly_trends': monthly_trends,
        
        # Performance
        'levy_collection_target': levy_collection_target,
        'levy_trend': round(levy_trend, 1)
    }
    
    return Response(response_data)