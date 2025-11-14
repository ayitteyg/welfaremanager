# actionunit/management/commands/create_customsuperuser.py
import os
import sys
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from welfare.models import Church

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser for WelfareManager system'

    def handle(self, *args, **options):
        self.stdout.write("Creating superuser for WelfareManager...")
        
        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING("Superuser already exists!")
            )
            return
        
        # Create superuser without church
        user = User.objects.create_superuser(
            username='admin',
            email='admin@ayigotech.com',
            password='admin123',  # Change this in production!
            name='System Administrator',
            phone='+233000000000',
            role='system_admin'
        )
        
        self.stdout.write(
            self.style.SUCCESS(f"Superuser created successfully: {user.username}")
        )
        self.stdout.write("You can now login to /admin with:")
        self.stdout.write("Username: admin")
        self.stdout.write("Password: admin123")