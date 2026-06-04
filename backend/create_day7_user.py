import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Role
from groups.models import Group
from django.core.cache import cache

User = get_user_model()

def create_user():
    username = "day7user"
    email = "day7user@example.com"
    password = "password123"
    
    # 1. Clean existing user if any
    User.objects.filter(username=username).delete()
    
    role, _ = Role.objects.get_or_create(name='Participant')
    group = Group.objects.filter(name='Group 4').first()
    
    now = timezone.now()
    onboarding_completed = now - timedelta(days=6)
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        role=role,
        group=group,
        has_completed_sociodemographic=True,
        onboarding_completed_at=onboarding_completed
    )
    
    # Clear caches
    cache.clear()
    
    print(f"Successfully created user: {username}")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print(f"Current Experiment Day: {user.current_experiment_day}")
    print(f"Due Milestone: {user.get_due_milestone}")

if __name__ == '__main__':
    create_user()
