#!/bin/sh
set -e

echo "⛩  Yasumi Restaurant Management System"
echo "──────────────────────────────────────"

echo "▸ Running database migrations..."
python manage.py migrate --noinput

echo "▸ Seeding tables and menu (safe — skips existing data)..."
python manage.py seed_yasumi

echo "▸ Collecting static files..."
python manage.py collectstatic --noinput --clear -v 0

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "▸ Ensuring superuser exists..."
  python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = '$DJANGO_SUPERUSER_USERNAME'
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u, '${DJANGO_SUPERUSER_EMAIL:-admin@yasumi.local}', '$DJANGO_SUPERUSER_PASSWORD')
    print('  ✓ Superuser created:', u)
else:
    print('  ✓ Superuser already exists:', u)
"
fi

echo "▸ Starting development server on port 8000..."
echo "──────────────────────────────────────"
exec python manage.py runserver 0.0.0.0:8000
