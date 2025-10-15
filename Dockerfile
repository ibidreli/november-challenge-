FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# copy only backend for this image
COPY backend/ ./backend/
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1
# create non-root user optional
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
