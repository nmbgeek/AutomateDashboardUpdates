#!/bin/bash

# Set default timezone if not provided
TIMEZONE="${TIMEZONE:-America/New_York}"

echo "Setting timezone to $TIMEZONE"
ln -snf /usr/share/zoneinfo/$TIMEZONE /etc/localtime
echo $TIMEZONE > /etc/timezone

# Set default cron schedule if not provided
CRON_SCHEDULE="${CRON_SCHEDULE:-0 6 * * *}"

# Create cron job
echo "$CRON_SCHEDULE root cd /app && /usr/bin/python3 /app/automateUpdate.py >> /proc/1/fd/1 2>&1" > /etc/cron.d/automate_update

# Give cron job correct permissions
chmod 0644 /etc/cron.d/automate_update
crontab /etc/cron.d/automate_update

# Check if RUN_AT_STARTUP is set to true (case-insensitive)
if [[ "${RUN_AT_STARTUP,,}" == "true" ]]; then
    echo "RUN_AT_STARTUP is set to true. Running automateUpdate.py now..."
    cd /app && /usr/bin/python3 /app/automateUpdate.py || echo "automateUpdate.py failed, continuing..."
fi

# Start cron in foreground mode
echo "Starting cron job with schedule: $CRON_SCHEDULE"
cron -f
