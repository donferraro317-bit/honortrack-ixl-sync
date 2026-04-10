FROM mcr.microsoft.com/playwright/python:v1.52.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY auth ./auth
COPY downloads ./downloads
COPY logs ./logs

ENV PYTHONUNBUFFERED=1
ENV PORT=10000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]