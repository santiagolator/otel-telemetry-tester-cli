import time
import json
import signal
import logging
from datetime import datetime
from typing import Dict, Any, Optional
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
        self.stats: Dict[str, Any] = {
            'traces': {'sent': 0, 'errors': 0, 'latencies': []},
            'metrics': {'sent': 0, 'errors': 0, 'latencies': []},
            'logs': {'sent': 0, 'errors': 0, 'latencies': []}
        }
        
        self._validate_counts()
        self._setup_resources()
        self._setup_exporters()
        self._setup_providers()
        self._setup_signal_handlers()

    def _validate_counts(self):
        """Valida que al menos un tipo de telemetría tenga count > 0"""
        if not any([self.args.trace_count > 0, 
                  self.args.metric_count > 0, 
                  self.args.log_count > 0]):
            raise ValueError("Debe especificar al menos un tipo de telemetría con count > 0")

    def _setup_resources(self):
        """Configura los recursos comunes"""
        self.resource = Resource.create({
            "service.name": self.args.service_name,
            "service.version": "1.0.0",
            "telemetry.tester.version": "1.0.0"
        })

    def _setup_exporters(self):
        """Configura los exporters según el protocolo"""
        self.headers = self._parse_headers()
        common_args = {
            'headers': self.headers,
            'timeout': self.args.timeout
        }

        if self.args.protocol == 'grpc':
            self._setup_grpc_exporters(common_args)
        else:
            self._setup_http_exporters(common_args)

    def _parse_headers(self):
        """Convierte los headers CLI en formato adecuado"""
        headers = []
        if self.args.header:
            for h in self.args.header:
                if '=' in h:
                    key, val = h.split('=', 1)
                    headers.append((key.strip(), val.strip()))
        return headers

    def _setup_grpc_exporters(self, common_args):
        """Configura exporters para gRPC"""
        self.trace_exporter = GRPCTraceExporter(
            endpoint=self.args.endpoint,
            insecure=not self.args.secure,
            **common_args
        )
        self.metric_exporter = GRPCMetricExporter(
            endpoint=self.args.endpoint,
            insecure=not self.args.secure,
            **common_args
        )
        self.log_exporter = GRPCLogExporter(
            endpoint=self.args.endpoint,
            insecure=not self.args.secure,
            **common_args
        )

    def _setup_http_exporters(self, common_args):
        """Configura exporters para HTTP"""
        base_url = self.args.endpoint
        self.trace_exporter = HTTPTraceExporter(
            endpoint=f"{base_url}/v1/traces",
            **common_args
        )
        self.metric_exporter = HTTPMetricExporter(
            endpoint=f"{base_url}/v1/metrics",
            **common_args
        )
        self.log_exporter = HTTPLogExporter(
            endpoint=f"{base_url}/v1/logs",
            **common_args
        )

    def _setup_providers(self):
        """Configura los proveedores de telemetría"""
        if self.args.trace_count > 0:
            self._setup_trace_provider()
        
        if self.args.metric_count > 0:
            self._setup_metric_provider()
        
        if self.args.log_count > 0:
            self._setup_log_provider()

    def _setup_trace_provider(self):
        """Configura el proveedor de traces"""
        trace_provider = TracerProvider(
            resource=self.resource
        )
        trace_provider.add_span_processor(
            BatchSpanProcessor(self.trace_exporter)
        )
        trace.set_tracer_provider(trace_provider)

    def _setup_metric_provider(self):
        """Configura el proveedor de métricas"""
        metric_reader = PeriodicExportingMetricReader(
            self.metric_exporter,
            export_interval_millis=5000
        )
        metric_provider = MeterProvider(
            resource=self.resource,
            metric_readers=[metric_reader]
        )
        metrics.set_meter_provider(metric_provider)

    def _setup_log_provider(self):
        """Configura el proveedor de logs"""
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

    def _setup_signal_handlers(self):
        """Configura el manejo de señales para shutdown"""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """Maneja señales de terminación"""
        print("\n🔴 Recibida señal de interrupción...")
        self.running = False

    def run(self):
        """Punto de entrada principal"""

        start_time = time.time()

        self._print_startup_message()
        
        try:
            if self.args.tail:
                self._run_continuous_mode()
            else:
                self._generate_single_batch()
                
        except Exception as e:
            logging.error(f"Error crítico: {str(e)}")
            raise
        finally:
            self.shutdown()
        
        self._print_cycle_stats(time.time() - start_time)

    def _run_continuous_mode(self):
        """Ejecuta en modo continuo hasta interrupción"""
        print("🔵 Modo continuo activado (Ctrl+C para detener)")
        print(f"🕒 Intervalo: {self.args.interval}s")
        print("------------------------------")
        while self.running:
            self._generate_single_batch()
            time.sleep(self.args.interval)

    def _generate_single_batch(self):
        """Genera un único batch de telemetría"""
        results = []
        if self.args.trace_count > 0:
            results.append(self.generate_traces())
        if self.args.metric_count > 0:
            results.append(self.generate_metrics())
        if self.args.log_count > 0:
            results.append(self.generate_logs())
        
        if not all(results) and not self.args.tail:
            raise RuntimeError("Falló uno o más tipos de telemetría")

    def generate_traces(self):
        """Genera traces con 3 segmentos: start, middle y end"""
        try:
            tracer = trace.get_tracer(__name__)
            for i in range(self.args.trace_count):
                with tracer.start_as_current_span(f"/otel-tester-trace/{self.args.protocol}") as root_span:
                    # Configurar atributos del trace principal
                    root_span.set_attribute("iteration", i)
                    root_span.set_attribute("service.name", self.args.service_name)
                    root_span.set_attribute("trace.type", "segmented")

                    # Primer segmento: Start
                    with tracer.start_as_current_span("start") as start_span:
                        start_span.set_attribute("segment", "initialization")
                        start_span.add_event("Segment started", {"timestamp": time.time_ns()})
                        self._simulate_work(0.02)  # Más tiempo en inicialización

                        # Segundo segmento: Middle (como hijo de start)
                        with tracer.start_as_current_span("middle") as middle_span:
                            middle_span.set_attribute("segment", "processing")
                            middle_span.add_event("Data processing", {"items": i * 10})
                            self._simulate_work(0.05)  # Mayor carga en procesamiento

                            # Tercer segmento: End (como hijo de middle)
                            with tracer.start_as_current_span("end") as end_span:
                                end_span.set_attribute("segment", "finalization")
                                end_span.add_event("Cleanup resources")
                                self._simulate_work(0.01)  # Menos tiempo en finalización

                    self.stats['traces']['sent'] += 1

                    if self.args.verbose:
                        print(f"✅ Trace {i+1} generado")

            return True

        except Exception as e:
            self.stats['traces']['errors'] += self.args.trace_count
            logging.error(f"Error en traces: {str(e)}")
            return False

    def generate_metrics(self):
        """Genera la cantidad especificada de métricas"""
        try:
            meter = metrics.get_meter(__name__)
            counter = meter.create_counter("otel.tester.counter")
            for i in range(self.args.metric_count):
                counter.add(1, {"iteration": i, "protocol": self.args.protocol})
                self._simulate_work(0.001)
                self.stats['metrics']['sent'] += 1
                if self.args.verbose:
                    print(f"✅ Métrica {i+1} generada")
            return True
        except Exception as e:
            self.stats['metrics']['errors'] += self.args.metric_count
            logging.error(f"Error en métricas: {str(e)}")
            return False

    def generate_logs(self):
        """Genera la cantidad especificada de logs"""
        try:
            logger = logging.getLogger(__name__)
            levels = [logging.INFO, logging.WARNING, logging.ERROR]
            messages = ["Inicio de proceso batch", "Advertencia: recurso limitado", "Error crítico en módulo"]
            for i in range(self.args.log_count):
                log_level = levels[i % 3]
                log_data = {
                    "iteration": i,
                    "service": self.args.service_name,
                    "timestamp": datetime.now().isoformat(),
                    "protocol": self.args.protocol
                }
                logger.log(
                    log_level,
                    messages[i % 3],
                    extra={"custom_dimensions": json.dumps(log_data), "severity_number": log_level * 10}
                )
                self._simulate_work(0.005)
                self.stats['logs']['sent'] += 1
            return True
        except Exception as e:
            self.stats['logs']['errors'] += self.args.log_count
            logging.error(f"Error en logs: {str(e)}")
            return False

    def _simulate_work(self, base_duration: float):
        """Simula carga de trabajo variable"""
        time.sleep(base_duration * (1 + (self.stats['traces']['sent'] % 3)))

    def _print_startup_message(self):
        """Muestra el mensaje inicial"""
        print(f"\n🚀 Iniciando envío de telemetría")
        print("------------------------------")
        if self.args.verbose:
            print(f"\n🔧 Configuración:")
            print(f"  - Endpoint: {self.args.endpoint}")
            print(f"  - Protocolo: {self.args.protocol.upper()}")
            print(f"  - Secure: {'✅' if self.args.secure else '❌'}")
            print(f"\n📦 Total a enviar:")
            print(f"  - Traces: {self.args.trace_count or 'N/A'}")
            print(f"  - Métricas: {self.args.metric_count or 'N/A'}")
            print(f"  - Logs: {self.args.log_count or 'N/A'}")
            print(f"{'\n🔁  Modo: Continuo' if self.args.tail else '\n1️⃣  Modo: Single batch'}")
            print("------------------------------")
            

    def _print_cycle_stats(self, duration: float):
        """Muestra estadísticas del ciclo"""
        print(f"\n⏱️  Ciclo completado en {duration:.2f}s")
        print(f"  - Traces enviados: {self.stats['traces']['sent']}")
        print(f"  - Métricas enviadas: {self.stats['metrics']['sent']}")
        print(f"  - Logs enviados: {self.stats['logs']['sent']}")
        print("------------------------------")

    def shutdown(self):
        """Cierra los recursos de forma segura"""
        if hasattr(self, '_shutdown'):
            return

        self._shutdown = True
        if self.args.verbose:
            print("\n🔒 Iniciando shutdown...")
        
        try:
            if self.args.trace_count > 0:
                trace.get_tracer_provider().shutdown()
            if self.args.metric_count > 0:
                metrics.get_meter_provider().shutdown()
            if self.args.log_count > 0:
                from opentelemetry._logs import get_logger_provider
                logger_provider = get_logger_provider()
                if logger_provider:
                    logger_provider.shutdown()

            if self.args.verbose:
                print("✅ Recursos liberados correctamente")

        except Exception as e:
            print(f"⚠️ Error durante shutdown: {str(e)}")