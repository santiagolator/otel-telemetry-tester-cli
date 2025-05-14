import time
import json
import signal
import logging
from typing import Dict, Any
import concurrent.futures
import threading
from threading import Lock
from tqdm import tqdm
import random
from opentelemetry import trace, metrics
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Status, StatusCode
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

        self.parallelism = args.parallel
        self.lock = Lock()  # Para estadísticas thread-safe

    def _thread_safe_update_stats(self, telemetry_type: str, success: bool):
        """Actualiza estadísticas de manera segura para hilos"""
        with self.lock:
            if success:
                self.stats[telemetry_type]['sent'] += 1
            else:
                self.stats[telemetry_type]['errors'] += 1

    def _parallel_execute(self, func, count: int, telemetry_type: str):
        """Ejecuta una función en paralelo"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.parallelism) as executor:
            futures = [executor.submit(func, i) for i in range(count)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    self._thread_safe_update_stats(telemetry_type, result)
                except Exception as e:
                    self._thread_safe_update_stats(telemetry_type, False)
                    logging.error(f"Error en hilo: {str(e)}")
    
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
            export_interval_millis=1000 if self.args.tail else 5000
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
                #schedule_delay_millis=5000 if self.args.tail else None
                schedule_delay_millis=100 if not self.args.tail else 5000  # <-- Envío más rápido
            )
        )
        set_logger_provider(logger_provider)
        
        handler = LoggingHandler(
            level=logging.DEBUG,  # Capturar todos los niveles
            logger_provider=logger_provider
        )
        
        custom_logger = logging.getLogger("otel_tester")
        custom_logger.setLevel(logging.DEBUG)  # Aceptar todos los niveles
        custom_logger.addHandler(handler)
        custom_logger.propagate = False  # Evitar propagación a root logger

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
            if self.args.log_count > 0 and not self.args.tail:
                time.sleep(0.2)  # Dar tiempo para el último envío
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
        """Genera traces con errores aleatorios en los spans"""
        try:
            tracer = trace.get_tracer(__name__)
            lock = threading.Lock()
            error_probability = 0.3  # 30% de probabilidad de error

            def _generate_single_trace(trace_id: int):
                try:
                    with tracer.start_as_current_span(f"/otel-tester-trace/{self.args.protocol}") as root_span:
                        # Decidir si este trace tendrá error
                        has_error = random.random() < error_probability
                        error_type = random.choice(["client", "server", "timeout"]) if has_error else None

                        root_span.set_attribute("iteration", trace_id)
                        root_span.set_attribute("service.name", self.args.service_name)
                        root_span.set_attribute("trace.type", "segmented-parallel")

                        # Segmento Start
                        with tracer.start_as_current_span("start") as start_span:
                            self._simulate_work(0.02)
                            if has_error and random.random() < 0.5:  # 50% probabilidad de error en start
                                start_span.set_status(StatusCode.ERROR, "Error en inicialización")
                                start_span.add_event("error", attributes={
                                    "error.type": error_type,
                                    "error.message": "Fallo en el proceso de inicialización"
                                })

                            # Segmento Middle
                            with tracer.start_as_current_span("middle") as middle_span:
                                self._simulate_work(0.05)
                                if has_error and random.random() < 0.7:  # Mayor probabilidad en middle
                                    middle_span.record_exception(ValueError("Error de procesamiento"))
                                    middle_span.set_status(StatusCode.ERROR)

                                # Segmento End
                                with tracer.start_as_current_span("end") as end_span:
                                    self._simulate_work(0.01)
                                    if has_error and not (start_span.is_recording() and start_span.status.is_ok):
                                        end_span.set_attribute("error.propagated", True)
                                        end_span.update_name("end-failed")

                        # Actualizar estadísticas
                        with lock:
                            if has_error:
                                self.stats['traces']['errors'] += 1
                                root_span.set_status(StatusCode.ERROR)
                            else:
                                self.stats['traces']['sent'] += 1
                        
                        return not has_error

                except Exception as e:
                    # Manejo de errores reales
                    with lock:
                        self.stats['traces']['errors'] += 1
                    return False

            # Configurar paralelismo con barra de progreso
            with tqdm(total=self.args.trace_count, 
                    desc="🚀 Enviando traces", 
                    unit="trace",
                    disable=not self.args.verbose) as pbar:

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.args.parallel) as executor:
                    futures = [executor.submit(_generate_single_trace, i) 
                             for i in range(self.args.trace_count)]

                    # Actualizar barra conforme se completan
                    for future in concurrent.futures.as_completed(futures):
                        pbar.update(1)
                        try:
                            future.result()
                        except Exception as e:
                            pass  # Los errores ya se registraron en _generate_single_trace

            return True

        except Exception as e:
            logging.error(f"Error crítico en generación de traces: {str(e)}")
            return False#
    
    def generate_metrics(self):
        """Genera métricas en paralelo con barra de progreso"""
        try:
            meter = metrics.get_meter(__name__)
            counter = meter.create_counter("otel.tester.counter")

            lock = threading.Lock()

            def _generate_single_metric(metric_id: int):
                try:
                    # Usar diferentes tipos de métricas
                    counter.add(metric_id + 1, {"metric_id": metric_id, "protocol": self.args.protocol})
                    with lock:
                        self.stats['metrics']['sent'] += 1
                    return True
                except Exception as e:
                    with lock:
                        self.stats['metrics']['errors'] += 1
                    return False

            with tqdm(total=self.args.metric_count, 
                    desc="📈 Enviando métricas", 
                    unit="metric",
                    disable=not self.args.verbose) as pbar:

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.args.parallel) as executor:
                    futures = [executor.submit(_generate_single_metric, i) 
                             for i in range(self.args.metric_count)]

                    for future in concurrent.futures.as_completed(futures):
                        pbar.update(1)
                        future.result()

            return True

        except Exception as e:
            logging.error(f"Error crítico en métricas: {str(e)}")
            return False    
    
    def generate_logs(self):
        """Genera logs en paralelo con barra de progreso"""
        try:
            logger = logging.getLogger("otel_tester")
            log_levels = [logging.INFO, logging.WARNING, logging.ERROR, logging.DEBUG]
            lock = threading.Lock()

            messages = [
            "Inicio de proceso paralelo",
            "Advertencia de carga elevada",
            "Error crítico en hilo",
            "Conexion a base de datos"
            ]

            def _generate_single_log(log_id: int):
            #for i in range(self.args.log_count):
                try:
                    level = log_levels[log_id % 4]
                    structured_data = {
                        "log_id": log_id,
                        "service": self.args.service_name,
                        "thread": threading.get_ident(),
                        "protocol": self.args.protocol
                    }
                    logger.log(level, messages[log_id % 3], extra={
                        "custom_dimensions": json.dumps(structured_data)
                    })

                    if self.args.verbose and not self.args.all:
                        # Mostrar en consola el nivel real enviado
                        tqdm.write(f"Enviado log {log_id +1} | Level: {logging.getLevelName(level)}")

                    with lock:
                        self.stats['logs']['sent'] += 1
                    return True
                except Exception as e:
                    with lock:
                        self.stats['logs']['errors'] += 1
                    return False
            
            with tqdm(total=self.args.log_count, 
                desc="📝 Enviando logs", 
                unit="log",
                disable=not self.args.verbose) as pbar:
            
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.args.parallel) as executor:
                    futures = [executor.submit(_generate_single_log, i) 
                             for i in range(self.args.log_count)]

                    for future in concurrent.futures.as_completed(futures):
                        pbar.update(1)
                        future.result()

            return True

        except Exception as e:
            logging.error(f"Error crítico en logs: {str(e)}")
            return False

    def _simulate_work(self, base_duration: float):
        """Simula carga de trabajo variable"""
        time.sleep(base_duration * (1 + (self.stats['traces']['sent'] % 3)))

    def _print_startup_message(self):
        """Muestra el mensaje inicial"""
        print(f"\n🚀 Iniciando envío de telemetría")
        print("------------------------------")
        if self.args.verbose:
            print(f"\n🔧 Configuración")
            print(f" ↳ Endpoint: {self.args.endpoint} | Protocolo: {self.args.protocol.upper()} | Secure: {'✅' if self.args.secure else '❌'}")
            print(f"\n📦 Total a enviar:")
            print(f" ↳ Traces: {self.args.trace_count or 'N/A'} | Métricas: {self.args.metric_count or 'N/A'} | Logs: {self.args.log_count or 'N/A'}")
            print(f"\n🔁  Modo:")
            print(f" ↳ Continuo | Paralelismo: {self.args.parallel}" if self.args.tail else f" ↳ Single batch | Paralelismo: {self.args.parallel}")
            print(f"------------------------------\n")
            
    def _print_cycle_stats(self, duration: float):
        """Muestra estadísticas del ciclo"""
        print(f"\n⏱️  Ciclo completado en {duration:.2f}s")
        print(f" ↳ Traces enviados: {self.stats['traces']['sent']} | Métricas enviadas: {self.stats['metrics']['sent']} | Logs enviados: {self.stats['logs']['sent']}")

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
                metrics.get_meter_provider().force_flush()
            if self.args.log_count > 0:
                from opentelemetry._logs import get_logger_provider
                logger_provider = get_logger_provider()
                if logger_provider:
                    logger_provider.force_flush()
                    logger_provider.shutdown()

            if self.args.verbose:
                print("✅ Recursos liberados correctamente")

        except Exception as e:
            print(f"⚠️ Error durante shutdown: {str(e)}")