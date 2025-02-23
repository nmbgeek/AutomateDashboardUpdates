# Use the official Playwright image with Python
#https://mcr.microsoft.com/en-us/artifact/mar/playwright/python/
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

# Install cron
RUN apt-get update && apt-get install -y cron tzdata && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script
COPY automateUpdate.py .

# Copy the cron setup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
