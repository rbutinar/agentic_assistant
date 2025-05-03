# --- Stage 1: Build React frontend ---
FROM node:18 AS frontend-build

# Set working directory inside the container
WORKDIR /app/frontend

# Install frontend dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# Copy all frontend files and build the React app
COPY frontend ./
RUN npm run build

# --- Stage 2: Build Python backend ---
FROM python:3.11-slim AS backend

# Set working directory
WORKDIR /app

# Install OS-level dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy entire backend source code
COPY . .

# Copy frontend static build from previous stage
COPY --from=frontend-build /app/frontend/build ./frontend_build

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Expose FastAPI's default port
EXPOSE 8000

# Set environment variables (if needed)
ENV PYTHONUNBUFFERED=1

# Launch FastAPI app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
