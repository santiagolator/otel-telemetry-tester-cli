# OpenTelemetry Telemetry Tester CLI

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![PyPI Version](https://img.shields.io/pypi/v/otel-telemetry-tester-cli)](https://pypi.org/project/otel-telemetry-tester-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

            _       _       _       _                     _                    _            _            
       ___ | |_ ___| |     | |_ ___| | ___ _ __ ___   ___| |_ _ __ _   _      | |_ ___  ___| |_ ___ _ __ 
      / _ \| __/ _ \ |_____| __/ _ \ |/ _ \ '_ ` _ \ / _ \ __| '__| | | |_____| __/ _ \/ __| __/ _ \ '__|
     | (_) | ||  __/ |_____| ||  __/ |  __/ | | | | |  __/ |_| |  | |_| |_____| ||  __/\__ \ ||  __/ |   
      \___/ \__\___|_|      \__\___|_|\___|_| |_| |_|\___|\__|_|   \__, |      \__\___||___/\__\___|_|   
                                                                   |___/ hecho con ❤️ por Santiago Lator 

Herramienta CLI para probar implementaciones de OpenTelemetry enviando datos de telemetría (traces, métricas, logs) a backends compatibles.

## Características Principales

- **Envía 3 tipos de telemetría**:
  - Traces con estructura compleja y errores simulados
  - Métricas tipo `counter`
  - Logs estructurados con múltiples niveles
- **Soporte para protocolos gRPC y HTTP** 
- **Modo continuo (tail)** para pruebas de larga duración
- **Paralelismo configurable** para simulaciones de alta carga
- **Conexiones seguras** con TLS/SSL y autenticación flexible
- **Compatibilidad** con New Relic, Grafana, Jaeger, Datadog y otros backends OTLP

## Instalación

```bash
pip install otel-telemetry-tester-cli
```

## Uso basico

```bash
otel-tester --endpoint production:4317 \
  --protocol grpc \
  --secure \
  --header "api-key=TU_API_KEY" \
  --trace-count 5 \
  --parallel 8
```

## Argumentos principales

Para ver el listado de argumentos posibles:

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
|`--tail`, `-t`          |Ejecución continua hasta interrupción	|False	        |                 |

### Configuración de cantidades y tipos de telemetria
|Argumento	|Descripción	|Default	|Ejemplo|
|----|-----|-----|-----|
|`--all`, `-a`	|Envía la misma cantidad para todos los tipos de telemetría	|1	|10|
|`--trace-count`, `-tc`	|Número de traces a generar	|1	|10|
|`--metric-count`, `-mc`	|Número de métricas a generar	|1	|50|
|`--log-count`, `-lc`	|Número de logs a generar	|1	|100|
|`--interval`, `-i`	|Intervalo entre envíos (segundos)	|0	|0.5|

### Opciones Avanzadas
|Argumento	|Descripción	|Default	|Ejemplo|
|----|-----|-----|-----|
|`--parallel`	| Hilos de ejecución paralela	|1	|10|
|`--header`, `-h`	|Headers personalizados	|1	|`Authorization=Bearer XYZ`|
|`--verbose`, `-v`	|Modo detallado	|	||

---

## 🧩 Estructura de los Datos
### 🔍 Traces
- 3 spans jerárquicos por trace:
  ```bash
  Start Span: Inicialización del proceso
    └── Middle Span: Procesamiento principal
        └── End Span: Finalización y limpieza
  ```
- Atributos personalizados
- Errores simulados:
  - 30% de probabilidad de error en spans
  - Tipos: `client`, `server`, `timeout`
  - Registro de excepciones y códigos de estado
    ```python
    span.set_status(StatusCode.ERROR)
    span.record_exception(ValueError("Simulated error"))
    ```

### 📊 Métricas
- Tipos soportados:
  - Counter: `otel.tester.counter`
  - Otros _coming soon_

- Atributos dinámicos:
  ```python
  counter.add(value, {"environment": "prod", "metric_id": id})
  ```

### 📝 Logs
- Niveles de log:
  - `INFO`: Mensajes operativos
  - `WARN`: Advertencias de sistema
  - `ERROR`: Errores críticos

- Dimensiones custom:

  ```python
  {
    "log_id": 123,
    "service": "auth-service",
    "thread": 45678,
    "protocol": "grpc"
  }
  ```

---

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

---

## ⚡ Paralelismo y Rendimiento
### Implementación
- ThreadPoolExecutor para ejecución concurrente
- Barras de progreso con `tqdm` para monitoreo
- Locks para estadísticas thread-safe

```python
with ThreadPoolExecutor(max_workers=args.parallel) as executor:
    futures = [executor.submit(task, i) for i in range(count)]
```

### Configuración Recomendada
|Escenario|	`--parallel`	| Descripción|
|---|---|---|
|Pruebas locales|	2-4	| Balance entre carga y recursos|
|Entorno CI/CD	|8-12	| Ejecución rápida en sistemas dedicados|
|Stress testing	|16+	| Máxima carga (requiere recursos suficientes)|

### Estadísticas de Rendimiento
```text
🚀 Enviando traces: 100%|██████| 500/500 [00:08<00:00, 58.23trace/s]
📈 Enviando métricas: 100%|████| 1000/1000 [00:02<00:00, 452.34metric/s]
📝 Enviando logs: 100%|██████| 2000/2000 [00:04<00:00, 487.12log/s]
```

---

# 🚨 Ejemplos Avanzados

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
otel-tester --tail \
  --log-count 5000 \
  --interval 0.1 \
  --parallel 16 \
  --service-name "stress-test"
```

Enviar con autenticación y seguridad:

```bash
otel-tester --endpoint https://observability.corp.com:443 \
  --protocol http \
  --secure \
  --header "X-API-Key=corp-key-123" \
  --header "X-Environment=prod" \
  -a 1000 \
  --parallel 24
```

# Licencia
Distribuido bajo licencia MIT. Ver LICENSE para más detalles.