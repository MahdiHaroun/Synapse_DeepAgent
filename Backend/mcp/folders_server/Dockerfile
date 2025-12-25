FROM python:3.12-slim
WORKDIR /app

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


RUN apt-get update && \
    apt-get install -y fonts-dejavu && \
    rm -rf /var/lib/apt/lists/*

# Copy current directory
COPY . /app

# Set Python path
ENV PYTHONPATH=/app

EXPOSE 3005

CMD ["python", "server.py"]
