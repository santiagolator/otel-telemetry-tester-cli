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
  --header "api-key=API_KEY" \
  --trace-count 5
```

### Argumentos principales

Para ver el listado de argumentos posibles

```bash
otel-tester --help
```

| Argumento     | Descripcion                    | Valores por defecto | Ejemplo               |
|----------------|--------------------------------|---------------------|-----------------------|
| `--endpoint`, `-e`    | Endpoint del collector OTLP    | Requerido           | otlp.nr-data.net:4317 |
| `--protocol` , `-p`   | Protocolo de comunicación      | grpc                | http                  |
| `--service-name` | Nombre del servicio            | otel-test-service   | my-awesome-service    |
| `--secure`       | Usar conexión TLS/SSL          | False               |                       |
| `--timeout `     | Timeout de conexión (segundos) | 10                  | 15                    |
| `--header`       | Headers en formato clave=valor |                     | Api-Key=abc123        |
|`--tail`, `-t`          |Ejecución continua hasta interrupción	|False	        |                 |
|`--verbose`, `-v`	       |Mostrar detalles de ejecución	  |False                |  |

### Configuración de cantidades y tipos de telemetria
|Argumento	|Descripción	|Default	|Ejemplo|
|----|-----|-----|-----|
|`--all`, `-a`	|Envía la misma cantidad para todos los tipos de telemetría	|1	|10|
|`--trace-count`, `-traces`	|Número de traces a generar	|1	|10|
|`--metric-count`, `-metrics`	|Número de métricas a generar	|1	|50|
|`--log-count`, `-logs`	|Número de logs a generar	|1	|100|
|`--interval`	|Intervalo entre envíos (segundos)	|0	|0.5|

## Ejemplos avanzados

Envio de traces y metricas en modo continuo:

```bash
otel-tester --tail \
  --endpoint collector:4317 \
  --protocol grpc \
  --trace-count 5 \
  --metric-count 100 \
  --interval 0.5 \
  --verbose
```

Enviar todos los tipos de telemetría:

```bash
otel-tester --endpoint localhost:4317 \
  --protocol grpc \
  --all 10 
```

"Prueba de stress" con logs:

```bash
otel-tester --endpoint localhost:4317 \
  --log-count 1000 \
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
  -metrics 100 \
  -traces 10 \
  -logs 50
```

### Modo Continuo (Tail)
Ejecuta la herramienta en segundo plano para monitoreo continuo:

```bash
otel-tester --tail \
  --endpoint otlp.nr-data.net:4317 \
  --protocol grpc \
  --trace-count 10 \
  ---metric-count 200 \
  --interval 1.5 \
```

#### Características del modo tail:

🕹️ Control con Ctrl+C para detención limpia

📊 Estadísticas en tiempo real con --verbose

🔄 Reintentos automáticos en errores transitorios

📦 Optimización de recursos para ejecuciones prolongadas

# Licencia
Distribuido bajo licencia MIT. Ver LICENSE para más detalles.