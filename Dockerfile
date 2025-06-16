# Use a slim Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_RUN_PORT=9000 \
    FLASK_RUN_HOST=0.0.0.0

# Create app directory
WORKDIR /AstroSpace

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app code into the container
COPY . .

# Expose the port
EXPOSE 9000

# Set environment variable so Flask knows what app to run
ENV FLASK_APP=AstroSpace

# Use environment variables at runtime (via docker-compose or container template)
# These will override any hardcoded values in config.py if you use os.environ in config

# Run the app
CMD ["flask", "run"]