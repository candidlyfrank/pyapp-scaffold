#!/bin/sh
set -eu

curl -fsS http://localhost/django/health/ >/dev/null
curl -fsS http://localhost/fastapi/health >/dev/null
echo "production smoke checks passed"
