import argparse
import logging
from .sender import TelemetrySender

def parse_args():
    parser = argparse.ArgumentParser(
        description='OpenTelemetry Telemetry Tester - Envía datos de prueba a backends OTLP',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Configuración básica
    parser.add_argument('-e','--endpoint', required=True,
                      help='Endpoint del collector (ej: otlp.nr-data.net:4317)')
    parser.add_argument('-p','--protocol', choices=['grpc', 'http'], default='grpc',
                      help='Protocolo de comunicación')
    parser.add_argument('--service-name', default='otel-tester-service',
                      help='Nombre del servicio en los recursos')
    parser.add_argument('--secure', action='store_true',
                      help='Usar TLS/SSL para la conexión')
    parser.add_argument('--timeout', type=int, default=10,
                      help='Timeout de conexión en segundos')
    
    # Tipos de telemetría
    parser.add_argument('-a','--all', type=int, metavar='COUNT',
                      help='Envía la misma cantidad para todos los tipos de telemetría')
    parser.add_argument('-traces','--trace-count', type=int, default=0,
                      help='Número total de traces a generar (sobrescribe --all)')
    parser.add_argument('-metrics','--metric-count', type=int, default=0,
                      help='Número total de métricas a generar (sobrescribe --all)')
    parser.add_argument('-logs','--log-count', type=int, default=0,
                      help='Número total de logs a generar (sobrescribe --all)')
    
    # Modo de operación
    parser.add_argument('-t','--tail', action='store_true',
                      help='Ejecución continua hasta interrupción')
    parser.add_argument('--interval', type=float, default=1.0,
                      help='Intervalo entre ciclos en segundos (solo en modo tail)')
    
    # Configuración avanzada
    parser.add_argument('--header', action='append',
                      help='Headers en formato clave=valor (ej: Api-Key=abc123)')
    parser.add_argument('-v', '--verbose', action='store_true',
                      help='Mostrar detalles de ejecución')
    
    return parser.parse_args()

def validate_args(args):
    """Valida los argumentos proporcionados"""
    error_messages = []

    # Aplicar --all si se especificó
    if args.all is not None:
        if args.all < 0:
            error_messages.append("El valor de --all debe ser ≥ 0")
        
        # Sobrescribir solo los counts no especificados
        if args.trace_count == 0:
            args.trace_count = args.all
        if args.metric_count == 0:
            args.metric_count = args.all
        if args.log_count == 0:
            args.log_count = args.all

    # Validación común
    if not any([args.trace_count > 0, args.metric_count > 0, args.log_count > 0]):
        error_messages.append("Debe especificar al menos un tipo de telemetría con count > 0")
    
    if args.tail and args.interval <= 0:
        error_messages.append("El intervalo debe ser mayor que 0 en modo tail")
    
    if args.protocol == 'http' and not args.endpoint.startswith(('http://', 'https://')):
        args.endpoint = f"http://{args.endpoint}"
    
    if error_messages:
        raise ValueError("\n".join(error_messages))

def main():
    try:
        args = parse_args()
        validate_args(args)
        
        # Configurar logging básico
        logging.basicConfig(
            level=logging.DEBUG if args.verbose else logging.INFO,
            format='%(levelname)s - %(message)s' if args.verbose else '%(message)s'
        )
        
        sender = TelemetrySender(args)
        sender.run()
        
        if not args.tail:
            print("\n✅ Ejecución completada exitosamente")
    
    except KeyboardInterrupt:
        print("\n🛑 Ejecución interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {str(e)}")
        exit(1)


def banner():

    banner = r"""
            _       _       _       _                     _                    _            _            
       ___ | |_ ___| |     | |_ ___| | ___ _ __ ___   ___| |_ _ __ _   _      | |_ ___  ___| |_ ___ _ __ 
      / _ \| __/ _ \ |_____| __/ _ \ |/ _ \ '_ ` _ \ / _ \ __| '__| | | |_____| __/ _ \/ __| __/ _ \ '__|
     | (_) | ||  __/ |_____| ||  __/ |  __/ | | | | |  __/ |_| |  | |_| |_____| ||  __/\__ \ ||  __/ |   
      \___/ \__\___|_|      \__\___|_|\___|_| |_| |_|\___|\__|_|   \__, |      \__\___||___/\__\___|_|   
                                                                   |___/                                 
    """
    
    print(banner)

if __name__ == "__main__":
    banner()
    main()