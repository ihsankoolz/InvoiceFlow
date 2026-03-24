# Generated gRPC stubs are placed here at Docker build time.
# Run: python -m grpc_tools.protoc -I proto --python_out=app/proto --grpc_python_out=app/proto proto/payment.proto
import sys
from pathlib import Path

# Add this directory to sys.path so generated stubs can find each other
# (protoc generates bare `import payment_pb2`, not relative imports)
sys.path.insert(0, str(Path(__file__).parent))
