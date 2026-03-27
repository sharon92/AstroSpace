FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /AstroSpace

# Install the published AstroSpace wheel plus the production WSGI stack.
ARG ASTROSPACE_VERSION=1.3.8
RUN pip install --upgrade pip \
    && pip install --no-cache-dir "astrospace==${ASTROSPACE_VERSION}" gunicorn gevent

# Expose app port
EXPOSE 9000

ENTRYPOINT ["python", "-m", "AstroSpace"]
CMD []
