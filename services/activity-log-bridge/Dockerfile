FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Add this line to fix the "Blank Terminal" issue
ENV PYTHONUNBUFFERED=1

CMD ["python", "bridge.py"]