#!/bin/sh
set -e

echo "Waiting for MySQL to be ready..."

until nc -z -v -w30 $DB_HOST $DB_PORT
do
  echo "Waiting for database connection at $DB_HOST:$DB_PORT..."
  sleep 5
done

echo "MySQL is up - running migrations..."
python manage.py migrate --noinput

# ---- Run the command passed by docker-compose ----
echo "Starting service: $@"
exec "$@"
