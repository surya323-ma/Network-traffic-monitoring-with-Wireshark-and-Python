FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bandwidth_monitor.py .

# Needs NET_ADMIN + NET_RAW + host networking to sniff real traffic:
# docker run --rm -it --network host --cap-add=NET_ADMIN --cap-add=NET_RAW \
#   --env-file ../.env bandwidth-capture

CMD ["python3", "bandwidth_monitor.py"]
