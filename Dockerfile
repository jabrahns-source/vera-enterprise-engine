FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV PYTHONPATH=/app/src
ENV VERA_DATA_DIR=/data

VOLUME ["/data"]

EXPOSE 8000

CMD ["uvicorn", "vera_engine.api:app", "--host", "0.0.0.0", "--port", "8000"]
