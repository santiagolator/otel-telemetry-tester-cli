import time
import signal
import logging
from typing import Optional
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
        self.running = True
        self.iteration = 0
        self.sent_traces = 0
        self.sent_metrics = 0
        self.sent_logs = 0
        
        self.resource = Resource.create({
            "service.name": args.service_name,
            "service.version": "1.0.0"
        })
        
        self.headers = self.parse_headers(args.header)
        self.setup_exporters()
        self.setup_providers()
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def parse_headers(self, header_list):
        """Convierte los headers en formato válido para los exporters"""
        headers = []
        if header_list:
            for header in header_list:
                if "=" in header:
                    key, value = header.split("=", 1)
                    headers.append((key.strip(), value.strip()))
        return headers

    def setup_exporters(self):
        protocol = self.args.protocol
        endpoint = self.args.endpoint
        
        common_args = {
            "headers": self.headers,
            "timeout": self.args.timeout,
            "compression": self.args.compress  # True/False
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
                BatchSpanProcessor(
                    self.trace_exporter,
                    schedule_delay_millis=5000 if self.args.tail else None
                )
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

        # Configurar logs
        if self.args.logs:
            logger_provider = LoggerProvider(
                resource=self.resource
            )
            logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(
                    self.log_exporter,
                    schedule_delay_millis=5000 if self.args.tail else None
                )
            )
            set_logger_provider(logger_provider)
            
            handler = LoggingHandler()
            logging.getLogger().addHandler(handler)
            logging.getLogger().setLevel(logging.INFO)

    def handle_signal(self, signum, frame):
        """Maneja señales de interrupción"""
        print("\n🔴 Recibida señal de terminación. Deteniendo...")
        self.running = False

    def should_continue(self):
        """Determina si debe continuar la ejecución"""
        if self.args.tail:
            return self.running
        return self.iteration < self.max_iterations()

    def max_iterations(self):
        """Calcula el máximo de iteraciones necesarias"""
        counts = []
        if self.args.traces and self.args.trace_count > 0:
            counts.append(self.args.trace_count)
        if self.args.metrics and self.args.metric_count > 0:
            counts.append(self.args.metric_count)
        if self.args.logs and self.args.log_count > 0:
            counts.append(self.args.log_count)
        return max(counts) if counts else 0

    def generate_telemetry(self):
        """Ejecuta el proceso principal de generación de telemetría"""
        self.print_startup_message()
        
        try:
            while self.should_continue():
                start_time = time.time()
                
                if self.args.traces:
                    self.generate_traces()
                
                if self.args.metrics:
                    self.generate_metrics()
                
                if self.args.logs:
                    self.generate_logs()
                
                self.iteration += 1
                self.print_iteration_stats(start_time)
                
                if self.args.interval > 0 and self.should_continue():
                    time.sleep(self.args.interval)
        
        except Exception as e:
            print(f"❌ Error crítico: {str(e)}")
            raise
        
        finally:
            self.shutdown()

    def generate_traces(self):
        """Genera un lote de traces"""
        tracer = trace.get_tracer(__name__)
        for i in range(self.args.trace_count):
            with tracer.start_as_current_span(f"/otel-tester-trace") as span:
                span.set_attribute("iteration", self.iteration)
                span.set_attribute("batch", i)
                self.sent_traces += 1
                time.sleep(0.01)  # Simular trabajo

    def generate_metrics(self):
        """Genera un lote de métricas"""
        meter = metrics.get_meter(__name__)
        counter = meter.create_counter("otel.tester.metric")
        for i in range(self.args.metric_count):
            counter.add(i, {"iteration": self.iteration})
            self.sent_metrics += 1

    def generate_logs(self):
        """Genera un lote de logs"""
        logger = logging.getLogger(__name__)
        log_levels = ['INFO', 'WARNING', 'ERROR']
        for i in range(self.args.log_count):
            level = log_levels[i % 3]
            msg = f"Log batch {self.iteration} - {i}"
            logger.log(
                getattr(logging, level),
                msg,
                extra={"iteration": self.iteration}
            )
            self.sent_logs += 1

    def print_startup_message(self):
        """Muestra el mensaje inicial"""
        print("🚀 Iniciando envío de telemetría")
        if self.args.tail:
            print("🔵 Modo continuo activado (Ctrl+C para detener)")
            print(f"📦 Tamaño de lote: "
                  f"Traces: {self.args.trace_count}/batch | "
                  f"Métricas: {self.args.metric_count}/batch | "
                  f"Logs: {self.args.log_count}/batch")
        else:
            print(f"🔢 Modo por lotes: {self.max_iterations()} iteraciones")

    def print_iteration_stats(self, start_time):
        """Muestra estadísticas de la iteración"""
        if self.args.verbose:
            duration = time.time() - start_time
            print(f"\n🔄 Iteración {self.iteration} completada")
            print(f"⏱️  Duración: {duration:.2f}s")
            print(f"📤 Enviados: "
                  f"Traces: {self.sent_traces} | "
                  f"Métricas: {self.sent_metrics} | "
                  f"Logs: {self.sent_logs}")

    def run(self):
        """Punto de entrada principal"""
        try:
            self.generate_telemetry()
        except Exception as e:
            print(f"❌ Error en ejecución: {str(e)}")
            raise
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Cierra los recursos de forma segura"""
        try:
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

                print("\n✅ Shutdown completado. Recursos liberados")
        
        except Exception as e:
            print(f"⚠️ Error durante el shutdown: {str(e)}")