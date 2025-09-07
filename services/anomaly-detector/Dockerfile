FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src /app/src

# This service will likely be run as a scheduled task or a long-running process
# For now, we'll just provide a placeholder command
CMD ["python", "-u", "src/main.py"]
