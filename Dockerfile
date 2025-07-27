FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /AstroSpace

# Install dependencies (add gevent too, to avoid resource exhaustion)
RUN pip install --upgrade pip \
    && pip install --upgrade astrospace gunicorn gevent

# Expose app port
EXPOSE 9000

CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:9000", "--timeout", "120", "--worker-class", "gevent", "AstroSpace:create_app()"]