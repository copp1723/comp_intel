FROM python:3.12-slim

# Install system dependencies required for Playwright/Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers with system dependencies
RUN python -m playwright install --with-deps chromium

# Copy application code
COPY . .

# Set Playwright to run in headless mode with Docker-friendly flags
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/ms-playwright/chromium-*/chrome-linux/chrome

# Start background worker
CMD ["python", "worker.py"]
