from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from core.config import JaegerSettings


jaeger_settings = JaegerSettings()


def configure_tracer() -> None:
    trace.set_tracer_provider(
        TracerProvider(resource=Resource.create({"service.name": jaeger_settings.service_name_auth}))
    )
    provider = trace.get_tracer_provider()
    provider.add_span_processor(
        BatchSpanProcessor(
            JaegerExporter(
                collector_endpoint=jaeger_settings.dsn,
            )
        )
    )
    if jaeger_settings.debug:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
