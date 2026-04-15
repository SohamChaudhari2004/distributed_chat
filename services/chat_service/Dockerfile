FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir grpcio grpcio-tools redis
COPY protos /app/protos
COPY compile_protos.py /app/
COPY services/chat_service /app/services/chat_service
RUN python compile_protos.py
CMD ["python", "services/chat_service/server.py"]