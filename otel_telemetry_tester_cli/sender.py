import time
import logging
from opentelemetry import trace, metrics
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCTraceExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as GRPCMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter as GRPCLogExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPTraceExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as HTTPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter as HTTPLogExporter
from opentelemetry.sdk.resources import Resource

class TelemetrySender:
    def __init__(self, args):
        self.args = args
        self.resource = Resource.create({
            "service.name": args.service_name,
            "service.version": "1.0.0"
        })
        self.headers = self.parse_headers(args.header)
        
        self.setup_exporters()
        self.setup_providers()

    def parse_headers(self, header_list):
        """Convierte los headers en formato válido para los exporters"""
        if not header_list:
            return []
        headers = []
        for header in header_list:
            if "=" not in header:
                continue
            key, value = header.split("=", 1)
            headers.append((key.strip(), value.strip()))
        return headers

    def setup_exporters(self):
        protocol = self.args.protocol
        endpoint = self.args.endpoint
        
        common_args = {
            "headers": self.headers,
            "timeout": self.args.timeout
        }

        if protocol == 'grpc':
            self.trace_exporter = GRPCTraceExporter(
                endpoint=endpoint, 
                insecure=not self.args.secure,
                **common_args
            )
            self.metric_exporter = GRPCMetricExporter(
                endpoint=endpoint,
                insecure=not self.args.secure,
                **common_args
            )
            self.log_exporter = GRPCLogExporter(
                endpoint=endpoint,
                insecure=not self.args.secure,
                **common_args
            )
        else:
            self.trace_exporter = HTTPTraceExporter(
                endpoint=f"{endpoint}/v1/traces",
                **common_args
            )
            self.metric_exporter = HTTPMetricExporter(
                endpoint=f"{endpoint}/v1/metrics",
                **common_args
            )
            self.log_exporter = HTTPLogExporter(
                endpoint=f"{endpoint}/v1/logs",
                **common_args
            )

    def setup_providers(self):
        # Configurar traces
        if self.args.traces:
            trace_provider = TracerProvider(
                resource=self.resource
            )
            trace_provider.add_span_processor(
                BatchSpanProcessor(self.trace_exporter)
            )
            trace.set_tracer_provider(trace_provider)

        # Configurar metrics
        if self.args.metrics:
            metric_reader = PeriodicExportingMetricReader(
                self.metric_exporter,
                export_interval_millis=self.args.metric_interval
            )
            metric_provider = MeterProvider(
                resource=self.resource,
                metric_readers=[metric_reader]
            )
            metrics.set_meter_provider(metric_provider)

        # Configurar logs (parte corregida)
        if self.args.logs:
            # Crear proveedor de logs
            logger_provider = LoggerProvider(
                resource=self.resource
            )
            
            # Añadir procesador de logs
            logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(self.log_exporter)
            )
            
            # Configurar proveedor global
            set_logger_provider(logger_provider)
            
            # Integrar con logging estándar
            handler = LoggingHandler(
                logger_provider=logger_provider
            )
            logging.getLogger().addHandler(handler)
            logging.getLogger().setLevel(logging.INFO)

    def generate_traces(self):
        tracer = trace.get_tracer(__name__)
        for i in range(self.args.trace_count):
            with tracer.start_as_current_span(f"RootSpan-{i}") as span:
                span.set_attribute("iteration", i)
                span.set_attribute("environment", "test")
                with tracer.start_as_current_span(f"ChildSpan-{i}"):
                    time.sleep(0.1)
                    if i % 2 == 0:
                        span.add_event("Even iteration processed")
                if self.args.interval > 0 and i < self.args.trace_count - 1:
                    time.sleep(self.args.interval)

    def generate_metrics(self):
        meter = metrics.get_meter(__name__)
        counter = meter.create_counter("test.counter")
        histogram = meter.create_histogram(
            "test.duration",
            unit="ms",
            description="Request processing duration"
        )
        
        for i in range(self.args.metric_count):
            counter.add(i, {"type": "test", "iteration": i})
            histogram.record(i * 10, {"environment": "staging"})
            if self.args.interval > 0 and i < self.args.metric_count - 1:
                time.sleep(self.args.interval)

    def generate_logs(self):
        logger = logging.getLogger(__name__)
        log_levels = ['INFO', 'WARNING', 'ERROR']
        
        for i in range(self.args.log_count):
            level = log_levels[i % 3]
            message = f"Test log message {i} - {level}"
            
            if level == 'INFO':
                logger.info(message, extra={"iteration": i})
            elif level == 'WARNING':
                logger.warning(message, extra={"iteration": i})
            else:
                logger.error(message, extra={"iteration": i})
            
            if self.args.interval > 0 and i < self.args.log_count - 1:
                time.sleep(self.args.interval)

    def run(self):
        try:
            start_time = time.time()
            
            if self.args.traces:
                print(f"Generando {self.args.trace_count} traces...")
                self.generate_traces()
            
            if self.args.metrics:
                print(f"Generando {self.args.metric_count} métricas...")
                self.generate_metrics()
            
            if self.args.logs:
                print(f"Generando {self.args.log_count} logs...")
                self.generate_logs()
            
            print(f"Proceso completado en {time.time() - start_time:.2f} segundos")
        
        except Exception as e:
            print(f"Error: {str(e)}")
        
        finally:
            self.shutdown()

    def shutdown(self):
        # Shutdown para traces
        if self.args.traces:
            trace.get_tracer_provider().shutdown()
        
        # Shutdown para métricas
        if self.args.metrics:
            metrics.get_meter_provider().shutdown()
        
        # Shutdown para logs
        if self.args.logs:
            from opentelemetry._logs import get_logger_provider
            logger_provider = get_logger_provider()
            if logger_provider:
                logger_provider.shutdown()
        
        # Limpiar handlers de logging
        if self.args.logs:
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                if isinstance(handler, LoggingHandler):
                    root_logger.removeHandler(handler)