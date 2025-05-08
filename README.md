# OpenTelemetry Telemetry Tester CLI

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![PyPI Version](https://img.shields.io/pypi/v/otel-telemetry-tester-cli)](https://pypi.org/project/otel-telemetry-tester-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Herramienta CLI para probar implementaciones de OpenTelemetry enviando datos de telemetría (traces, metrics, logs) a backends compatibles.

## Características Principales

✅ Envío de Traces, Métricas y Logs  
✅ Modo continuo (tail) para pruebas prolongadas  
✅ Soporte para protocolos gRPC y HTTP  
✅ Configuración de headers personalizados (API Keys, JWT, etc)  
✅ Compresión gzip para transmisiones eficientes  
✅ Generación de datos de prueba parametrizable  
✅ Estadísticas en tiempo real con modo verbose  
✅ Intervalos de envío configurables  
✅ Conexiones seguras (TLS/SSL)  
✅ Compatible con principales backends (New Relic, Grafana, Jaeger, etc)

## Instalación

```bash
pip install otel-telemetry-tester-cli
```

## Uso basico

```bash
otel-tester --endpoint otlp.nr-data.net:4317 \
  --protocol grpc \
  --secure \
  --header "api-key=TU_API_KEY" \
  --traces \
  --trace-count 5
```

### Argumentos principales

Para ver el listado de argumentos posibles

```bash
otel-tester --help
```

| Argumento     | Descripcion                    | Valores por defecto | Ejemplo               |
|----------------|--------------------------------|---------------------|-----------------------|
| `--endpoint`     | Endpoint del collector OTLP    | Requerido           | otlp.nr-data.net:4317 |
| `--protocol`     | Protocolo de comunicación      | grpc                | http                  |
| `--service-name` | Nombre del servicio            | otel-test-service   | my-awesome-service    |
| `--secure`       | Usar conexión TLS/SSL          | False               |                       |
| `--timeout `     | Timeout de conexión (segundos) | 10                  | 15                    |
| `--header`       | Headers en formato clave=valor |                     | Api-Key=abc123        |
|`--tail`	           |Ejecución continua hasta interrupción	|False	        |                 |
|`--compress`	       |Habilitar compresión gzip	      |False	              |  |
|`--verbose`	       |Mostrar detalles de ejecución	  |False                |  |

### Tipos de telemetria

|Argumento	|Descripción|
|-------------|----------------------|
|`--traces`	|Habilitar envío de traces|	
|`--metrics`	|Habilitar envío de métricas|	
|`--logs`	|Habilitar envío de logs|

### Configuración de Cantidades
|Argumento	|Descripción	|Default	|Ejemplo|
|----|-----|-----|-----|
|`--trace-count`	|Número de traces a generar	|1	|10|
|`--metric-count`	|Número de métricas a generar	|1	|50|
|`--log-count`	|Número de logs a generar	|1	|100|
|`--interval`	|Intervalo entre envíos (segundos)	|0	|0.5|
|`--metric-interval`	|Intervalo de exportación de métricas (ms)	|5000	|1000|

## Ejemplos avanzados

Modo continuo con compresión:

```bash
otel-tester --tail \
  --endpoint collector:4317 \
  --protocol grpc \
  --compress \
  --traces --trace-count 5 \
  --metrics --metric-count 100 \
  --interval 0.5 \
  --verbose
```

Enviar todos los tipos de telemetría:

```bash
otel-tester --endpoint localhost:4317 \
  --protocol grpc \
  --traces --metrics --logs \
  --trace-count 10 \
  --metric-count 20 \
  --log-count 15 \
  --interval 0.2
```

"Prueba de stress" con logs:

```bash
otel-tester --endpoint localhost:4317 \
  --logs --log-count 1000 \
  --interval 0.1 \
  --service-name "stress-test"
```

Enviar con autenticación y seguridad:

```bash
otel-tester --endpoint https://api.monitoring.com:443 \
  --protocol http \
  --secure \
  --header "Authorization=Bearer eyJhbGci..." \
  --header "X-Custom-Header=value" \
  --traces --metrics \
  --trace-count 10 \
  --metric-count 50
```

### Modo Continuo (Tail)
Ejecuta la herramienta en segundo plano para monitoreo continuo:

```bash
otel-tester --tail \
  --endpoint otlp.nr-data.net:4317 \
  --protocol grpc \
  --traces --trace-count 10 \
  --metrics --metric-count 200 \
  --interval 1.5 \
  --compress
```

#### Características del modo tail:

🕹️ Control con Ctrl+C para detención limpia

📊 Estadísticas en tiempo real con --verbose

🔄 Reintentos automáticos en errores transitorios

📦 Optimización de recursos para ejecuciones prolongadas

# Licencia
Distribuido bajo licencia MIT. Ver LICENSE para más detalles.