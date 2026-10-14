# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Dependencies exported from pyproject.toml + uv.lock (no project secrets).
COPY requirements-cloud-run.txt ./

# Install dependencies
RUN pip install --no-cache-dir --require-hashes -r requirements-cloud-run.txt

# Copy application code
COPY weather.py ./

# Expose port (Cloud Run will override this)
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1

# Run the application
CMD ["python", "weather.py"]
