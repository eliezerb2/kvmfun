# ---- Builder Stage ----
# This stage installs build tools, compiles Python packages, and creates a virtual environment.
FROM python:3.11.7-slim AS builder

# Install build-time system dependencies.
# 'build-essential' is a meta-package that includes gcc, make, and C library headers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libvirt-dev \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment.
ENV VENV_PATH=/opt/venv
RUN python -m venv $VENV_PATH

# Copy and install Python dependencies into the virtual environment.
COPY requirements.txt .
RUN $VENV_PATH/bin/pip install --no-cache-dir -r requirements.txt


# ---- Final Stage ----
# This stage creates the final, minimal production image.
FROM python:3.11.7-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install ONLY runtime system dependencies.
# 'libvirt-client' provides the necessary shared libraries (.so files) for the application to run.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libvirt-clients \
    openssh-client \
    qemu-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built virtual environment from the builder stage.
ENV VENV_PATH=/opt/venv
COPY --from=builder $VENV_PATH $VENV_PATH

# Copy the application source code.
COPY src/ ./src/

# Change ownership to non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Add the virtual environment's bin directory to the PATH.
ENV PATH="$VENV_PATH/bin:$PATH"
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]