FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies for sqlite/C extensions if required by packages
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Final runtime stage
FROM python:3.12-slim

WORKDIR /app

# Copy wheels and install
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Add non-root user for security
RUN addgroup --system appgroup && adduser --system --no-create-home --group appuser

# Copy application files (secrets and db are excluded via .dockerignore)
COPY src/ src/
COPY scripts/daemon.py scripts/daemon.py
COPY config/ config/
COPY main.py .
COPY schema.sql .

# Create volume mount points and set permissions
RUN mkdir -p /app/logs /app/config && \
    chown -R appuser:appgroup /app

USER appuser

# Environment flags for Python
ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/app/app_data.db

# Entrypoint via our custom polling script
CMD ["python", "scripts/daemon.py"]
