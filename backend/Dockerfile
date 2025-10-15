FROM python:3.11-slim
WORKDIR /app

# dependencies file is expected in the backend build context
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy backend sources (context is backend/)
COPY . .

ENV PYTHONUNBUFFERED=1

# Start the FastAPI app (main.py is in the backend root)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
