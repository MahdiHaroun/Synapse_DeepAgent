FROM python:3.12-slim

# system deps (if needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install deps first (better cache)
COPY requirements.txt .
RUN pip install --cache-dir=/root/.cache/pip -r requirements.txt 

# copy ONLY what we need
COPY Backend/api Backend/api
COPY src src
COPY Synapse_RAG Synapse_RAG
COPY main.py .

# make imports work
ENV PYTHONPATH=/app

EXPOSE 8070

CMD ["python", "-m", "Backend.api.main"]
