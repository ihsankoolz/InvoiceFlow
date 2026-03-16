FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Generate gRPC stubs from proto at build time
RUN python -m grpc_tools.protoc \
    -I proto \
    --python_out=proto \
    --grpc_python_out=proto \
    proto/payment.proto
# Add proto dir to PYTHONPATH so generated payment_pb2_grpc.py can find payment_pb2
ENV PYTHONPATH=/app/proto
CMD ["python", "worker.py"]
