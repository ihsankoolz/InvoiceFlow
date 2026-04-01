import os
import sys

# Add temporal-worker root to path so activities/clients/config are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
