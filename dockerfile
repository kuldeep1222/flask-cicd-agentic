# Use official Python base image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Copy all files to container
COPY . .

# Install dependencies
RUN pip install --upgrade pip && \
    pip install Flask && \
    pip install pytest

# Expose Flask port
EXPOSE 5000

# Run Flask app (ensure flask_cicd.py has app.run(host="0.0.0.0", port=5000))
CMD ["python", "flask_cicd.py"]


