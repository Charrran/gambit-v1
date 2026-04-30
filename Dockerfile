FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Start command - PORT is injected by Railway at runtime
CMD sh -c "echo Starting on port $PORT && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
