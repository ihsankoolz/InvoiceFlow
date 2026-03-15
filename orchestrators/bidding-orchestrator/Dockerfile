FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Generate gRPC stubs from proto at build time
RUN python -m grpc_tools.protoc \
    -I proto \
    --python_out=app/proto \
    --grpc_python_out=app/proto \
    proto/payment.proto
EXPOSE 5011
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5011"]
