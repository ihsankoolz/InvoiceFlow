"""OpenTelemetry tracing setup with OTLP/Tempo exporter.

Falls back silently if the opentelemetry packages are not installed in the
service image — so adding this to a service is always safe.
"""

import logging
import os

logger = logging.getLogger(__name__)


def setup_tracing(service_name: str) -> None:
    """Initialise OTel tracing for *service_name*.

    Exports spans to Tempo via OTLP HTTP.  The endpoint defaults to
    ``http://tempo:4318/v1/traces`` and can be overridden with
    ``OTEL_EXPORTER_OTLP_ENDPOINT``.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4318/v1/traces")
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        logger.info("OpenTelemetry tracing configured for '%s' → %s", service_name, endpoint)
    except ImportError:
        logger.debug(
            "opentelemetry packages not installed — tracing disabled for '%s'", service_name
        )
