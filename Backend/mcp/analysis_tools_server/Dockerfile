FROM python:3.12-slim
WORKDIR /app

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy current directory
COPY . /app

# Set Python path
ENV PYTHONPATH=/app

EXPOSE 3040

CMD ["python", "server.py"]

