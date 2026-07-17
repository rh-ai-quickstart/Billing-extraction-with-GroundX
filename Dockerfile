# Use a lightweight Python 3.12 base image
FROM python:3.12-slim

# Create a non-root user for security
RUN groupadd --gid 1001 appuser && \
    adduser --uid 1001 --gid 1001 --disabled-password --gecos "" --home /app appuser

# Set working directory
WORKDIR /app

# Install Python dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App package + notebook prompt machinery (manager.py / prompts/) used at runtime
COPY apps ./apps
COPY manager.py .
COPY prompts ./prompts
COPY test-docs ./test-docs
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Streamlit default port
EXPOSE 8501

# apps.ui must be importable from /app; prompts/manager resolve from WORKDIR
ENV PYTHONPATH=/app
# CORS/XSRF disabled for OpenShift edge-terminated HTTPS reverse proxy
CMD ["streamlit", "run", "apps/ui/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
