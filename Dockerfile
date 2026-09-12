# Use official Python slim image
FROM python:3.11-slim

# Create a non-root user (HuggingFace Spaces requirement)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Set working directory
WORKDIR /home/user/app

# Install dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user . .

# Create data directory for SQLite
RUN mkdir -p /home/user/app/backend/data
RUN mkdir -p /home/user/app/data

# Environment variables
ENV RECOVERY_DEMO_MODE=true
ENV PORT=7860

# Expose the port
EXPOSE 7860

# Run the server (run.py uses uvicorn on port 8000, so we should run uvicorn directly on 7860)
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
