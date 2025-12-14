# Single image used for both: FastAPI backend + Streamlit dashboard
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (kept minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000 8501

# Default command is the API (compose overrides for dashboard)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
