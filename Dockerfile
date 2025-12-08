# Use python 3.12 slim image
FROM python:3.12-slim

# Copy uv binary from the official uv image (Best Practice)
# This places /uv in /bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory to the project root (/app)
WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock* ./

# Install packages using uv sync
RUN /bin/uv sync

# Copy the rest of the application code
COPY . .

# Expose the port (documentation only)
EXPOSE 8001

# Use shell form to allow environment variable expansion
# Cloud Run will set PORT=8001 based on your --port flag
CMD /bin/uv run uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8001}