FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir grpcio grpcio-tools fastapi uvicorn websockets
COPY protos /app/protos
COPY compile_protos.py /app/
COPY services/gateway /app/services/gateway
RUN python compile_protos.py
CMD ["uvicorn", "services.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]