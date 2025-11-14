# Multi-stage build for optimal image size
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Install system dependencies required for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy application code
COPY src/ ./src/
COPY pyproject.toml .

# Create directory for configuration (will be mounted as volume)
RUN mkdir -p /root/.config/blackout_tracker_mcp

# Set up proper permissions
RUN chmod -R 755 /app

# Add a non-root user for running the application (optional but recommended)
RUN useradd -m -u 1000 mcpuser && \
    chown -R mcpuser:mcpuser /app /root/.config/blackout_tracker_mcp

# Switch to non-root user
USER mcpuser

# Health check (optional - checks if Python can import the server module)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app'); from src.server import app; print('OK')" || exit 1

# Entry point for the MCP server
# The server uses stdio for communication
ENTRYPOINT ["python", "-m", "src.server"]

# Note: No CMD needed as the server will run via ENTRYPOINT
# and will communicate via stdin/stdout
