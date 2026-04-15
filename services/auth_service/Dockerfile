FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir grpcio grpcio-tools
COPY protos /app/protos
COPY compile_protos.py /app/
COPY services/auth_service /app/services/auth_service
RUN python compile_protos.py
CMD ["python", "services/auth_service/server.py"]