FROM python:3.12-slim
WORKDIR /app

# Copy and install Synapse_RAG as a package
COPY Synapse_RAG/ /app/Synapse_RAG/
RUN pip install --no-cache-dir -e /app/Synapse_RAG/

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server script
COPY server.py /app/

EXPOSE 3010

CMD ["python", "server.py"]
