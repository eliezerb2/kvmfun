FROM python:3.11.7-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install system dependencies with pinned versions
RUN apt-get update && apt-get install -y \
    libvirt-dev=9.0.0-4 \
    pkg-config=1.8.1-1 \
    gcc=4:12.2.0-3 \
    qemu-utils=1:7.2+dfsg-7+deb12u5 \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Change ownership to non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]