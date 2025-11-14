from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

@admin.register(Church)
class ChurchAdmin(admin.ModelAdmin):
    list_display = ['name', 'welfare_name', 'location', 'email']
    search_fields = ['name', 'welfare_name']

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['phone_number', 'name', 'church', 'is_welfare_admin', 'is_church_admin', 'is_member']
    list_filter = ['is_welfare_admin', 'is_church_admin', 'is_member', 'church']
    search_fields = ['phone_number', 'name']
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal info', {'fields': ('name', 'contact', 'church')}),
        ('Roles', {'fields': ('is_welfare_admin', 'is_church_admin', 'is_member')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'name', 'password1', 'password2', 'church'),
        }),
    )
    
    ordering = ['-created_at']



@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone_number', 'user', 'church', 'gender', 'status', 'date_joined']
    list_filter = ['church', 'gender', 'status', 'date_joined']
    search_fields = ['full_name', 'phone_number']

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'member', 'date', 'receipt_type', 'amount', 'year']
    list_filter = ['receipt_type', 'year', 'date']
    search_fields = ['receipt_number', 'member__full_name']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'member', 'event_date', 'venue', 'levy_amount', 'is_levy_paid']
    list_filter = ['event_type', 'event_date', 'is_levy_paid']
    search_fields = ['member__full_name', 'venue', 'description']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_type', 'payee_name', 'date', 'amount', 'payment_method', 'church']
    list_filter = ['payment_type', 'payment_method', 'date']
    search_fields = ['payee_name', 'description']


@admin.register(YearlyDues)
class YearlyDuesAdmin(admin.ModelAdmin):
    list_display = ['church', 'year', 'monthly_amount', 'created_by', 'created_at']
    list_filter = ['church', 'year']
    search_fields = ['church__name']