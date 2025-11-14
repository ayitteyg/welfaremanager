from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator

class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        
        # Auto-generate password if not provided
        if not password:
            password = self.get_default_password(phone_number)
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_welfare_admin', True)
        
        return self.create_user(phone_number, password, **extra_fields)

    def get_default_password(self, phone_number):
        """Generate default password based on phone number"""
        # Remove any non-digit characters and get last 6 digits
        digits = ''.join(filter(str.isdigit, phone_number))
        if len(digits) >= 6:
            return digits[-6:]  # Last 6 digits
        return "123456"  # Fallback default


    

class Church(models.Model):
    name = models.CharField(max_length=255)
    welfare_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    welfare_momo = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^0[0-9]{9}$', message='Enter a valid 10-digit mobile money number')]
    )
    church_momo = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r'^0[0-9]{9}$', message='Enter a valid 10-digit mobile money number')]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name




class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    phone_number = models.CharField(validators=[phone_regex], max_length=17, unique=True)
    name = models.CharField(max_length=255)
    
    # Church relationship
    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name='users')
    
    # User roles
    is_welfare_admin = models.BooleanField(default=False)
    is_church_admin = models.BooleanField(default=False)
    is_member = models.BooleanField(default=True)  # Default role
    
    # Django auth fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.phone_number})"
    
    def save(self, *args, **kwargs):
        # Ensure at least one role is set
        if not any([self.is_welfare_admin, self.is_church_admin, self.is_member]):
            self.is_member = True
        super().save(*args, **kwargs)




class Member(models.Model):
    MEMBER_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('transferred', 'Transferred'),
        ('deceased', 'Deceased'),
        ('privileged', 'Privileged'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name='members')
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='member_profile',
        null=True,  # Allow null initially for existing users
        blank=True
    )
    full_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)  # Keep for easy access
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    status = models.CharField(max_length=20, choices=MEMBER_STATUS, default='active')
    location = models.TextField(blank=True, null=True)
    date_joined = models.DateField(auto_now_add=True)  # Auto-set to creation date
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        unique_together = ['church', 'phone_number']  # Unique phone per church

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"

    def save(self, *args, **kwargs):
        # Auto-create user if doesn't exist and phone_number is provided
        if not self.user and self.phone_number:
            try:
                # Check if user already exists with this phone number
                user = CustomUser.objects.get(phone_number=self.phone_number)
                self.user = user
            except CustomUser.DoesNotExist:
                # Create new user with member role
                user = CustomUser.objects.create_user(
                    phone_number=self.phone_number,
                    name=self.full_name,
                    church=self.church,
                    is_member=True,
                    is_welfare_admin=False,
                    is_church_admin=False
                )
                self.user = user
        
        # Ensure phone_number stays in sync with user
        if self.user and self.user.phone_number != self.phone_number:
            self.phone_number = self.user.phone_number
            
        super().save(*args, **kwargs)




class Receipt(models.Model):
    RECEIPT_TYPES = [
        ('monthly_dues', 'Monthly Dues'),
        ('transport_levy', 'Transport Levy'),
        ('donation', 'Donation'),
        ('passbook', 'Passbook'),
        ('other', 'Other'),
    ]
    
    receipt_number = models.CharField(max_length=50, unique=True, blank=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField()
    receipt_type = models.CharField(max_length=20, choices=RECEIPT_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    year = models.IntegerField()  # Year payment is for
    details = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Generate receipt number: CHURCH_INITIALS/YEAR/SEQ
            church_initials = ''.join(word[0].upper() for word in self.member.church.name.split()[:3])
            year = self.date.year
            last_receipt = Receipt.objects.filter(
                receipt_number__startswith=f"{church_initials}/{year}/"
            ).order_by('receipt_number').last()
            
            if last_receipt:
                last_seq = int(last_receipt.receipt_number.split('/')[-1])
                new_seq = last_seq + 1
            else:
                new_seq = 1
                
            self.receipt_number = f"{church_initials}/{year}/{new_seq:04d}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.receipt_number} - {self.member.full_name}"






class Event(models.Model):
    EVENT_TYPES = [
        ('funeral', 'Funeral'),
        ('wedding', 'Wedding'),
        ('child_dedication', 'Child Dedication'),
        ('sickness', 'Sickness'),
        ('other', 'Other'),
    ]
    
    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='events')
    event_date = models.DateField()
    venue = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    levy_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Transport levy for this event
    is_levy_paid = models.BooleanField(default=False)  # Track if levy has been collected
    
    # Audit fields
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-event_date', '-created_at']
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.member.full_name} ({self.event_date})"







class Payment(models.Model):
    PAYMENT_TYPES = [
        ('member_benefit', 'Member Benefit'),
        ('operational_expense', 'Operational Expense'),
        ('event_expense', 'Event Expense'),
        ('other', 'Other'),
    ]
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('check', 'Check'),
    ]
    
    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    
    # For member benefits
    beneficiary_member = models.ForeignKey(
        Member, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='benefits_received'
    )
    
    # For event-related payments
    related_event = models.ForeignKey(
        Event,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    
    # Payment details
    payee_name = models.CharField(max_length=255)  # Who received the payment
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    description = models.TextField(blank=True)
    
    # Supporting documents
    receipt_number = models.CharField(max_length=100, blank=True)  # External receipt number
    supporting_document = models.FileField(upload_to='payment_documents/', null=True, blank=True)
    
    # Audit fields
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.payment_type} - {self.payee_name} - {self.amount}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate that member benefits have a beneficiary member
        if self.payment_type == 'member_benefit' and not self.beneficiary_member:
            raise ValidationError({
                'beneficiary_member': 'Beneficiary member is required for member benefit payments.'
            })
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)





# models.py
class YearlyDues(models.Model):
    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name='yearly_dues')
    year = models.IntegerField()
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Audit fields
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['church', 'year']  # One dues amount per church per year
        ordering = ['-year']
        verbose_name_plural = 'Yearly dues'
    
    def __str__(self):
        return f"{self.church.name} - {self.year}: ${self.monthly_amount}/month"