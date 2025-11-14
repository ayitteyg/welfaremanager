from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import *


class ChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = '__all__'
        


class UserSerializer(serializers.ModelSerializer):
    church = ChurchSerializer(read_only=True)
    church_id = serializers.PrimaryKeyRelatedField(
        queryset=Church.objects.all(), 
        source='church', 
        write_only=True,
        required=False
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'phone_number', 'name', 'church', 'church_id',
            'is_welfare_admin', 'is_church_admin', 'is_member',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SignupSerializer(serializers.Serializer):
    # Church info
    church_name = serializers.CharField(max_length=255)
    welfare_name = serializers.CharField(max_length=255)
    location = serializers.CharField(max_length=255)
    church_email = serializers.EmailField()
    welfare_momo = serializers.CharField(max_length=15)  # Required
    church_momo = serializers.CharField(max_length=15, required=False, allow_blank=True)  # Optional
    
    
    # User info
    name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=17)

    def validate_phone_number(self, value):
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value
    
    
    def validate_welfare_momo(self, value):
        # Basic momo number validation
        if not value.startswith('0') or len(value) != 10:
            raise serializers.ValidationError("Please enter a valid mobile money number (10 digits starting with 0).")
        return value

    def validate_church_momo(self, value):
        if value and (not value.startswith('0') or len(value) != 10):
            raise serializers.ValidationError("Please enter a valid mobile money number (10 digits starting with 0).")
        return value
    

    def create(self, validated_data):
        # Create church first
        church = Church.objects.create(
            name=validated_data['church_name'],
            welfare_name=validated_data['welfare_name'],
            location=validated_data['location'],
            email=validated_data['church_email'],
            welfare_momo=validated_data['welfare_momo'],
            church_momo=validated_data.get('church_momo', '')  # Optional field
        )
        
        # Create user as welfare admin - password will be auto-generated
        user = CustomUser.objects.create_user(
            phone_number=validated_data['phone_number'],
            name=validated_data['name'],
            church=church,
            is_welfare_admin=True,
            is_member=False
        )
        
        
         # Automatically create Member record for this user
        Member.objects.create(
            church=church,
            user=user,
            full_name=validated_data['name'],
            phone_number=validated_data['phone_number'],
            gender='male',  # You might want to add this field to your signup form
            status='active',
            location=validated_data['location']
        )
        
        return user




class ChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = [
            'id', 'name', 'welfare_name', 'location', 'email', 
            'welfare_momo', 'church_momo', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'name', 'welfare_name', 'location', 'created_at', 'updated_at']



class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate(self, data):
        phone_number = data.get('phone_number')

        if phone_number:
            # Find user by phone number
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError("No account found with this phone number.")
            
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            
            # Auto-generate password from phone number (last 6 digits)
            digits = ''.join(filter(str.isdigit, phone_number))
            if len(digits) >= 6:
                auto_password = digits[-6:]
            else:
                auto_password = "123456"
            
            # Authenticate with auto-generated password
            auth_user = authenticate(phone_number=phone_number, password=auto_password)
            if auth_user:
                data['user'] = auth_user
            else:
                raise serializers.ValidationError("Unable to authenticate. Please try again.")
        else:
            raise serializers.ValidationError("Phone number is required.")

        return data



class MemberSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    church_name = serializers.CharField(source='church.name', read_only=True)

    class Meta:
        model = Member
        fields = [
            'id', 'church', 'church_name', 'user', 'user_details', 'full_name', 
            'phone_number', 'gender', 'status', 'location', 'date_joined',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'church']  # Add 'church' here



# serializers.py - Updated versions

class ReceiptSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    receipt_type_display = serializers.CharField(source='get_receipt_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)

    class Meta:
        model = Receipt
        fields = [
            'id', 'receipt_number', 'member', 'member_name', 'date', 'receipt_type',
            'receipt_type_display', 'amount', 'year', 'details', 'created_by',
            'created_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'receipt_number', 'created_at', 'created_by', 'created_by_name', 'member_name', 'receipt_type_display']
        
        # Frontend only needs to send these:
        # - member (ID)
        # - date
        # - receipt_type
        # - amount
        # - year
        # - details

class EventSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    church_name = serializers.CharField(source='church.name', read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'church', 'church_name', 'event_type', 'event_type_display', 'member',
            'member_name', 'event_date', 'venue', 'description', 'levy_amount',
            'is_levy_paid', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'church', 'church_name', 'created_at', 'updated_at', 'created_by', 'created_by_name', 'member_name', 'event_type_display']
        
        # Frontend only needs to send these:
        # - event_type
        # - member (ID)
        # - event_date
        # - venue
        # - description
        # - levy_amount
        # - is_levy_paid

class PaymentSerializer(serializers.ModelSerializer):
    beneficiary_name = serializers.CharField(source='beneficiary_member.full_name', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    event_description = serializers.CharField(source='related_event.description', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    church_name = serializers.CharField(source='church.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'church', 'church_name', 'payment_type', 'payment_type_display',
            'beneficiary_member', 'beneficiary_name', 'related_event', 'event_description',
            'payee_name', 'date', 'amount', 'payment_method', 'payment_method_display',
            'description', 'receipt_number', 'supporting_document', 'created_by',
            'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'church', 'church_name', 'created_at', 'updated_at', 'created_by', 
            'created_by_name', 'beneficiary_name', 'payment_type_display', 
            'payment_method_display', 'event_description'
        ]
        
        # Frontend only needs to send these:
        # - payment_type
        # - beneficiary_member (ID, optional for non-benefit payments)
        # - related_event (ID, optional)
        # - payee_name
        # - date
        # - amount
        # - payment_method
        # - description
        # - receipt_number (external receipt, optional)
        # - supporting_document (file, optional)


# serializers.py
class YearlyDuesSerializer(serializers.ModelSerializer):
    church_name = serializers.CharField(source='church.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)

    class Meta:
        model = YearlyDues
        fields = [
            'id', 'church', 'church_name', 'year', 'monthly_amount',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'created_by_name']