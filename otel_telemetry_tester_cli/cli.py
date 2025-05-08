import argparse
import logging
from .sender import TelemetrySender

def parse_args():
    parser = argparse.ArgumentParser(
        description='CLI para pruebas de telemetria para OpenTelemetry',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Configuración básica
    parser.add_argument('--endpoint', required=True,
                      help='Endpoint del collector OTLP (ej: localhost:4317)')
    parser.add_argument('--protocol', choices=['grpc', 'http'], default='grpc',
                      help='Protocolo de comunicación')
    parser.add_argument('--service-name', default='otel-tester-service',
                      help='Nombre del servicio en los recursos')
    parser.add_argument('--secure', action='store_true',
                      help='Usar conexión TLS/SSL')
    parser.add_argument('--timeout', type=int, default=10,
                      help='Timeout de conexión en segundos')
    
    # Headers
    parser.add_argument('--header', action='append',
                      help='Headers en formato clave=valor (ej: Api-Key=abc123)')
    
    # Tipos de telemetría
    parser.add_argument('--traces', action='store_true',
                      help='Habilitar envío de traces')
    parser.add_argument('--metrics', action='store_true',
                      help='Habilitar envío de métricas')
    parser.add_argument('--logs', action='store_true',
                      help='Habilitar envío de logs')
    
    # Cantidades
    parser.add_argument('--trace-count', type=int, default=1,
                      help='Traces por iteración (modo tail) o totales')
    parser.add_argument('--metric-count', type=int, default=1,
                      help='Métricas por iteración (modo tail) o totales')
    parser.add_argument('--log-count', type=int, default=1,
                      help='Logs por iteración (modo tail) o totales')
    
    # Intervalos
    parser.add_argument('--interval', type=float, default=1.0,
                      help='Intervalo entre iteraciones en segundos')
    parser.add_argument('--metric-interval', type=int, default=5000,
                      help='Intervalo de exportación de métricas en milisegundos')

    # Argumentos para modo tail
    parser.add_argument('--tail', action='store_true',
                      help='Ejecución continua hasta interrupción manual')
    parser.add_argument('--compress', action='store_true',
                      help='Habilitar compresión gzip para los exports')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Mostrar detalles de ejecución')
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    try:
        # Validar argumentos
        if not any([args.traces, args.metrics, args.logs]):
            raise ValueError("Debes especificar al menos un tipo de telemetría (--traces, --metrics, --logs)")
        
        # Configurar logging básico
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
        
        # Ejecutar el sender
        sender = TelemetrySender(args)
        sender.run()
        print("✅ Telemetría enviada exitosamente")
    
    except KeyboardInterrupt:
        print("\n🛑 Operación cancelada por el usuario")
        exit(130)
    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
        exit(1)
    finally:
        if 'sender' in locals():
            sender.shutdown()

if __name__ == "__main__":
    main()