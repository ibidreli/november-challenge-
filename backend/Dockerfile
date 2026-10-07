FROM python:3.11-slim
WORKDIR /app

# copy requirements from backend build context
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copy backend sources (build context is backend/)
COPY . .

ENV PYTHONUNBUFFERED=1

# Start the FastAPI app
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
