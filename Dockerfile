FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory (name doesn't matter much here)
WORKDIR /AstroSpace

# Install published package + gunicorn
RUN pip install --upgrade pip \
    && pip install --upgrade astrospace gunicorn

# Expose the port your app listens on
EXPOSE 9000

# Start the app using Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:9000", "AstroSpace:create_app()"]