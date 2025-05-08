# OpenTelemetry Telemetry Tester CLI

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![PyPI Version](https://img.shields.io/pypi/v/otel-telemetry-tester-cli)](https://pypi.org/project/otel-telemetry-tester-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Herramienta CLI para probar implementaciones de OpenTelemetry enviando datos de telemetría (traces, metrics, logs) a backends compatibles.

## Características Principales

✅ Envío de Traces, Metrics y Logs  
✅ Soporte para protocolos gRPC y HTTP  
✅ Configuración de headers personalizados (ej: API Keys)  
✅ Generación de datos de prueba parametrizable  
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

Generar carga continua de métricas:

```bash
otel-tester --endpoint collector:4317 \
  --metrics \
  --metric-count 1000 \
  --metric-interval 1000
```

Enviar con autenticación y seguridad:

```bash
otel-tester --endpoint https://collector:443 \
  --protocol http \
  --secure \
  --header "Authorization=Bearer TOKEN" \
  --traces \
  --trace-count 5
```

# Licencia
Distribuido bajo licencia MIT. Ver LICENSE para más detalles.