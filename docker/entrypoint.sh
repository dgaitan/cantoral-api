#!/bin/bash
set -euo pipefail

python manage.py collectstatic --noinput

if [ "${KAMAL_ROLE:-web}" = "web" ]; then
  python manage.py migrate --noinput
fi

exec "$@"
