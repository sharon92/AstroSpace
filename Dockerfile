FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /AstroSpace

# Install dependencies (add gevent too, to avoid resource exhaustion)
COPY requirements.txt /AstroSpace/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt gunicorn gevent

COPY AstroSpace /AstroSpace/AstroSpace

# Expose app port
EXPOSE 9000

ENTRYPOINT ["python", "-m", "AstroSpace"]
CMD []
