#!/bin/sh
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Creating superuser (if not exists)..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
import os
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@pims.local')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin')
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
if User.objects.filter(username=username).exists():
    print(f'Superuser {username} already exists.')
    from users.models import Role
    role, _ = Role.objects.get_or_create(name='Admin')
    u = User.objects.get(username=username)
    if u.role != role:
        u.role = role
        u.save(update_fields=['role'])
        print(f'Superuser {username} assigned to Admin role.')
elif User.objects.filter(email=email).exists():
    print(f'User with email {email} already exists.')
else:
    from users.models import Role
    role, _ = Role.objects.get_or_create(name='Admin')
    u = User.objects.create_superuser(username=username, email=email, password=password)
    u.role = role
    u.save(update_fields=['role'])
    print(f'Superuser {username} created and assigned to Admin role.')
"

echo "Starting Daphne (ASGI server)..."
exec daphne -b 0.0.0.0 -p 8000 core.asgi:application
