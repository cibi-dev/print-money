---
tipo: seguridad
categoria: estandar-devsecops
tags:
  - security
  - devsecops
  - sre
  - cwe
  - owasp
  - nist-ssdf
  - sast
  - testing
creado: 2026-08-27
actualizado: 2026-08-27
alcance: universal-todos-los-proyectos
---

# 🔒 SECURITY.md — Estándar Canónico de Seguridad Maestro

> **Instrucción para agentes IA:** Leer este documento **completo** antes de escribir cualquier línea de código. Todos los estándares son **obligatorios por diseño**, agnósticos al nombre del repositorio y vinculados deterministamente a las primitivas de código e imports utilizados. Ningún hito se aprueba con violaciones activas.

**Fuente de autoridad:** Estándares DevSecOps (OWASP ASVS 5.0, NIST SP 800-218 SSDF, CWE Top 25, SLSA L2).  
**Restricción operativa:** 100 % local, $0 de inversión, cero dependencias de APIs de IA externas o servicios de pago.

---

## 🧭 Matriz de Auto-Activación por Imports y Primitivas (Para Agentes IA)

El agente no clasifica el proyecto por su nombre comercial o slug de catálogo, sino por las **librerías y primitivas de E/S que importa o ejecuta**:

| Si el código utiliza o importa... | Guardrails Activados | Requisito Obligatorio Innegociable |
|---|---|---|
| `tarfile`, `zipfile`, `shutil.unpack_archive` | **#6** (CWE-409/59) | Extracción iterativa con `os.path.commonpath()`, cuotas duras (<500 MB, <10k archivos) y rechazo de symlinks fuera de sandbox. |
| `yaml`, `json`, `tomllib`, `pydantic` | **#7, CWE-502** | `yaml.safe_load()` exclusivo + Pydantic v2 `extra='forbid'` (<1 MB de documento para mitigar DoS). |
| `tempfile`, `fcntl`, `multiprocessing.Lock` | **#8** (CWE-377/362) | Nombres aleatorios `mkstemp()`, locks `fcntl.flock` con timeout ≤5s y cleanup garantizado vía `try/finally` + `atexit`. |
| `hashlib`, `hmac`, `secrets`, `cryptography` | **#9, CWE-208** | Comparación estricta con `hmac.compare_digest()`, entropía vía `secrets`/`os.urandom` y derivación de contraseñas con PBKDF2/Argon2. |
| `asyncio`, `httpx`, `socket`, `threading`, `n8n` | **#10, #14 (CWE-400/918)** | Semáforos y pools acotados, timeout en peticiones HTTP y denylist estricta contra SSRF (bloqueo de IPs privadas y metadata cloud). |
| `langgraph`, `langchain`, `google.genai`, `openai` | **#15, #16, #17** | Validación de entrada AST determinista, `extra='forbid'`, human-in-the-loop (`interrupt_before`) en mutaciones y `recursion_limit` $\le 4$. |
| `os.geteuid`, `os.setuid`, `pwd`, `systemd` | **#11, CWE-250/269** | Separación estricta: módulo de escáner sin root / remediador con verificación explícita de privilegios y drop de usuario. |
| `sqlite3`, `psycopg`, `sqlalchemy` | **OWASP DB** | Consultas 100% parametrizadas (prohibidos f-strings o interpolación en sentencias SQL). |
| `pickle`, `marshal`, `shelve` | **OWASP Memoria** | **PROHIBIDO** sobre datos no confiables o externos; serialización exclusiva vía JSON, esquemas Pydantic o `.npz` (`allow_pickle=False`). |
| Cualquier repositorio / paquete | **#1–5, #12, #13** | `.gitignore` canónico, cero secretos (CWE-798), sanitización logs (CWE-22), SAST Bandit (CWE-78), firma Git, lockfiles y manejo seguro de errores. |

---

## 1️⃣ Estándares Base de Seguridad (#1–5)

> **Política de Tolerancia Cero** (CWE-798 & SAST): Todo repositorio de código debe cumplir estos 5 estándares base desde su primer commit.

---

### #1 — `.gitignore` Canónico Reforzado

**Disparador:** Todo repositorio de código y árbol de trabajo Git.  
**Vector / CWE:** Fuga accidental de credenciales, claves criptográficas y bases de datos locales.

**Plantilla mínima obligatoria** — copiar a `.gitignore` de cada repositorio:

```gitignore
# Secretos & credenciales
.env*
*.pem
*.key
*.p12
*.token
*secret*
*credential*
*id_rsa*
*.pfx
*.crt

# Bases de datos & artefactos locales
*.db
*.db-wal
*.db-shm
*.sqlite

# Entornos virtuales, IDEs & caché
.venv/
venv/
.cache/
__pycache__/
*.pyc
*.pyo
.mypy_cache/
.pytest_cache/
.vscode/
.zcode/

# Artefactos de build & empaquetado
dist/
build/
*.egg-info/

# Reportes de escaneo sensibles
gitleaks-report.json
bandit-report.json
```

**Verificación:** `git ls-files --others --ignored --exclude-standard` — ningún archivo sensible debe figurar rastreado.

---

### #2 — Cero Secretos Hardcodeados (CWE-798)

**Disparador:** Todo archivo de código fuente, script, archivo de configuración o suite de tests.  
**Vector / CWE:** CWE-798 (Use of Hard-coded Credentials).

```python
# ❌ INCORRECTO — nunca hardcodear claves o rutas privadas
API_KEY = "ghp_abc123realtoken"
DB_PASSWORD = "mi_password_real"
conn = sqlite3.connect("/home/cibi/datos_reales.db")

# ✅ CORRECTO — leer siempre desde variables de entorno
import os

API_KEY = os.environ["API_KEY"]           # Falla explícita si no existe
DB_PATH = os.environ.get("DB_PATH", ":memory:")  # Default seguro para pruebas

# ✅ CORRECTO — en suites de pruebas usar únicamente mocks dummy
MOCK_TOKEN = "mock_token_test_123_safe"   # Token sintético; no activa gitleaks
MOCK_KEY   = "test_api_key_0000000000000"
```

**Verificación:** `gitleaks detect --source . --verbose` — resultado: `0 leaks found`.

---

### #3 — Sanitización de Logs & Defensa contra Path Traversal (CWE-22)

**Disparador:** Funciones que registren logs, formateen strings hacia stdout/stderr o lean rutas provistas por el usuario/red.  
**Vector / CWE:** CWE-22 (Improper Limitation of a Pathname to a Restricted Directory) & Fuga de PII en logs.

```python
import os
import logging

# ✅ CORRECTO — sanitización estricta de logs
def log_request(token: str, path: str) -> None:
    logging.info("Request recibida | token=[REDACTED] | path=%s", path)

# ✅ CORRECTO — validación determinista de Path Traversal (CWE-22)
def safe_open(base_dir: str, user_path: str) -> str:
    base    = os.path.abspath(base_dir)
    target  = os.path.abspath(os.path.join(base, user_path))
    # commonpath garantiza que el target resuelto reside estrictamente dentro de base
    if os.path.commonpath([base, target]) != base:
        raise ValueError(f"Path Traversal detectado: {user_path!r}")
    return target

# ❌ INCORRECTO — exposición de secretos y lectura de rutas sin sanear
# logging.info("Token: %s | ruta: %s", real_token, real_path)
# open(f"/data/{user_input}")  # Sin validación commonpath → Vulnerable a ../../
```

**Verificación:** `bandit -r . -ll --tests B108,B110` — detecta rutas no seguras.

---

### #4 — Escaneo Estático SAST & Dependencias (Bandit + pip-audit)

**Disparador:** Todo desarrollo en Python y ejecución de comandos del sistema operativo.  
**Vector / CWE:** CWE-78 (OS Command Injection) & Vulnerabilidades conocidas en dependencias (CVEs).

```python
# ❌ INCORRECTO — CWE-78: inyección de comandos en shell
import subprocess
user_input = "archivo.txt; rm -rf /"
# subprocess.run(f"cat {user_input}", shell=True)   # Peligro crítico

# ✅ CORRECTO — lista de argumentos + shell=False + timeout estricto
subprocess.run(
    ["cat", safe_path],   # Lista: sin expansión de shell
    shell=False,           # Explícito
    timeout=30,            # Cota temporal obligatoria
    capture_output=True,
    check=True,
)
```

**`pyproject.toml` — cotas de versión superiores obligatorias:**

```toml
[project]
dependencies = [
    "pydantic>=2.0,<3",
    "numpy>=1.26,<2",
    "pyyaml>=6.0,<7",
]
```

**Verificación:**
```bash
bandit -r . -ll                    # 0 issues de nivel MEDIUM o HIGH
pip-audit --strict                 # 0 vulnerabilidades conocidas
```

---

### #5 — Privacidad de Autoría Git

**Disparador:** Todo repositorio y configuración local de Git.  
**Vector / CWE:** Exposición de emails personales y falta de no-repudio en commits.

```bash
# Configuración por repositorio
git config user.email "cibi-dev@users.noreply.github.com"
git config user.name  "cibi-dev"
git config commit.gpgsign true   # Firma criptográfica GPG
```

**Verificación:** `git log --format="%ae" | head -5` — todos los commits deben mostrar `cibi-dev@users.noreply.github.com`.

---

## 2️⃣ Guardrails Avanzados de Seguridad Profunda (#6–13) — Fase 2

> Cubren vectores lógicos profundos que herramientas SAST como Bandit **no detectan** por sí solas.

---

### #6 — Hardening contra Archive/Tar Bombs & Symlink Escapes (CWE-409 & CWE-59)

**Disparador Técnico:** Proyectos que descompriman, inspeccionen o extraigan archivos comprimidos (TAR, ZIP, GZ, capas OCI de Docker).  
**Vector / CWE:** CWE-409 (Improper Handling of Highly Compressed Data / Bombs) & CWE-59 (Improper Link Resolution).

```python
import tarfile, os

TAR_MAX_BYTES   = 500 * 1024 * 1024   # Límite duro: 500 MB
TAR_MAX_MEMBERS = 10_000              # Límite duro: 10,000 archivos

# ❌ INCORRECTO — extractall sin filtrado permite sobrescritura y bombas de descompresión
# tarfile.open("archivo.tar.gz").extractall("/destino")

# ✅ CORRECTO — extracción iterativa segura con validación de sandbox
def safe_extract(tar_path: str, dest: str) -> None:
    dest_abs = os.path.realpath(dest)
    total_bytes, total_members = 0, 0

    with tarfile.open(tar_path, "r:*") as tf:
        for member in tf.getmembers():
            # Rechazo de rutas absolutas y secuencias de escape
            if member.name.startswith("/") or ".." in member.name:
                raise ValueError(f"Ruta peligrosa detectada: {member.name!r}")

            # Validación de enlaces simbólicos y duros
            if member.issym() or member.islnk():
                link_target = os.path.realpath(os.path.join(dest_abs, member.linkname))
                if os.path.commonpath([dest_abs, link_target]) != dest_abs:
                    raise ValueError(f"Symlink escapa del sandbox: {member.name!r}")

            # Protección contra bombas de descompresión
            total_bytes   += member.size
            total_members += 1
            if total_bytes > TAR_MAX_BYTES:
                raise ValueError("Tar bomb: cuota de tamaño total superada")
            if total_members > TAR_MAX_MEMBERS:
                raise ValueError("Tar bomb: cuota de número de archivos superada")

            # Extracción segura miembro a miembro
            f = tf.extractfile(member)
            if f:
                target = os.path.join(dest_abs, member.name)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "wb") as out:
                    out.write(f.read())
```

---

### #7 — Parser YAML Seguro & Deserialización Controlada (CWE-20 & CWE-502)

**Disparador Técnico:** Proyectos que lean o procesen manifiestos de configuración YAML, JSON o estructuras declarativas.  
**Vector / CWE:** CWE-502 (Deserialization of Untrusted Data) & CWE-20 (Improper Input Validation).

```python
import yaml
from pydantic import BaseModel

YAML_MAX_BYTES = 1 * 1024 * 1024  # Cota de 1 MB — mitiga Billion Laughs DoS

# ❌ INCORRECTO — yaml.load sin Loader seguro permite ejecución remota de código (RCE)
# data = yaml.load(open("config.yaml"))

# ✅ CORRECTO — safe_load + validación estricta de esquema Pydantic v2
class PipelineConfig(BaseModel):
    name: str
    steps: list[str]

    model_config = {"extra": "forbid"}  # Falla ante campos desconocidos o inyectados

def load_config(path: str) -> PipelineConfig:
    content = open(path, "rb").read()
    if len(content) > YAML_MAX_BYTES:
        raise ValueError("Archivo de configuración supera el límite de 1 MB")
    raw = yaml.safe_load(content)              # safe_load SIEMPRE
    return PipelineConfig.model_validate(raw)  # Validación tipada estricta
```

---

### #8 — Archivos Temporales Seguros & Locks de Concurrencia (CWE-377 & CWE-362)

**Disparador Técnico:** Módulos que generen archivos en `/tmp`, gestionen locks de procesos o ejecuten tareas concurrentes.  
**Vector / CWE:** CWE-377 (Insecure Temporary File) & CWE-362 (Race Condition / TOCTOU).

```python
import tempfile, fcntl, contextlib, atexit, os, signal

# ❌ INCORRECTO — rutas fijas predecibles en /tmp son vulnerables a symlink attacks
# tmp_path = "/tmp/deploy_lock"

# ✅ CORRECTO — tempfile con nombre aleatorio y cleanup garantizado
@contextlib.contextmanager
def secure_tempfile(suffix: str = ""):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        yield path
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

# ✅ CORRECTO — lock de archivo exclusivo con timeout anti-deadlock
LOCK_TIMEOUT_S = 5

def acquire_process_lock(lock_path: str):
    fd = open(lock_path, "w")
    try:
        signal.alarm(LOCK_TIMEOUT_S)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        signal.alarm(0)
    except (OSError, BlockingIOError):
        raise RuntimeError("No se pudo adquirir el lock exclusivo en el tiempo estipulado")
    return fd
```

---

### #9 — Higiene Criptográfica: Tiempo Constante & Entropía Segura (CWE-208, CWE-321 & CWE-330)

**Disparador Técnico:** Funciones que comparen hashes, generen tokens, session IDs, Trace-IDs, nonces o deriven claves.  
**Vector / CWE:** CWE-208 (Timing Attack), CWE-321 (Hard-coded Cryptographic Key), CWE-330 (Use of Insufficiently Random Values).

```python
import hmac, secrets, os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# ❌ INCORRECTO — comparación == es vulnerable a timing attacks; random no es seguro
# if hash_a == hash_b: ...
# token = random.token_hex(16)
# hashlib.md5(data) / hashlib.sha1(data)  # Algoritmos rotos prohibidos

# ✅ CORRECTO — comparación en tiempo constante
if hmac.compare_digest(hash_a, hash_b):  # Inmune a timing attacks
    pass

# ✅ CORRECTO — aleatoriedad criptográfica
token    = secrets.token_hex(32)          # Para tokens / session IDs
nonce    = os.urandom(12)                 # Para AES-256-GCM (12 bytes)
trace_id = secrets.token_bytes(16)        # W3C TraceContext Trace-ID (16 bytes)

# ✅ CORRECTO — derivación segura de contraseñas
def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,   # NIST SP 800-132 recomendación
    )
    return kdf.derive(password.encode())

# Algoritmos PERMITIDOS: AES-256-GCM, ChaCha20-Poly1305, SHA-256+, BLAKE3
# Algoritmos PROHIBIDOS: MD5, SHA-1, DES, 3DES, AES-ECB
```

---

### #10 — Cuotas de Recursos, Timeouts & Concurrencia Acotada (CWE-400 — Anti-DoS)

**Disparador Técnico:** Servidores HTTP, proxies inversos, listeners de red, colas de eventos o tareas concurrentes (`asyncio`/`threads`).  
**Vector / CWE:** CWE-400 (Uncontrolled Resource Consumption / Denial of Service).

```python
import asyncio, os
from concurrent.futures import ThreadPoolExecutor

# ❌ INCORRECTO — llamadas y tareas ilimitadas saturan memoria y descriptores
# await asyncio.gather(*unbounded_tasks)

# ✅ CORRECTO — concurrencia estrictamente acotada
MAX_WORKERS = min(32, (os.cpu_count() or 1) + 4)
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
sem = asyncio.Semaphore(MAX_WORKERS)

async def bounded_execution(coros):
    async def _run(coro):
        async with sem:
            return await coro
    return await asyncio.gather(*(_run(c) for c in coros))

# ✅ CORRECTO — timeout explícito en toda operación de E/S
async def safe_fetch(url: str) -> bytes:
    async with asyncio.timeout(10):  # Python 3.11+
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            return resp.content

# ✅ CORRECTO — rechazo preventivo de payloads HTTP excesivos
MAX_PAYLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
```

---

### #11 — Verificación de Privilegios & Separación Lector/Escritor (CWE-250 & CWE-269)

**Disparador Técnico:** Demonios, inspectores de sistema (`procfs`), herramientas de remediación y gestión de servicios (`systemd`).  
**Vector / CWE:** CWE-250 (Execution with Unnecessary Privileges) & CWE-269 (Improper Privilege Management).

```python
import os, sys, pwd

# ✅ CORRECTO — módulos de solo lectura operan sin root y advierten si se les eleva innecesariamente
def run_read_only_inspector():
    if os.geteuid() == 0:
        print("ADVERTENCIA DE SEGURIDAD: El escáner no requiere root.", file=sys.stderr)
    # Ejecución normal de auditoría...

# ✅ CORRECTO — módulos mutadores abortan limpiamente sin privilegios
def run_remediator():
    if os.geteuid() != 0:
        print("ERROR: La remediación requiere privilegios root explícitos.", file=sys.stderr)
        sys.exit(1)

# ✅ CORRECTO — drop de privilegios a usuario dedicado tras binding a puerto privilegiado (<1024)
def drop_privileges(user_name: str = "nobody"):
    target_user = pwd.getpwnam(user_name)
    os.setgroups([])                 # Limpiar grupos suplementarios primero
    os.setgid(target_user.pw_gid)
    os.setuid(target_user.pw_uid)
    assert os.getuid() != 0, "Fallo crítico: no se pudieron revocar privilegios root"
```

---

### #12 — Fijado de Dependencias con Hashes — Cadena de Suministro (SLSA L2)

**Disparador Técnico:** Gestión de dependencias en cualquier paquete de software.  
**Vector / CWE:** Ataques a la cadena de suministro (Supply Chain Attacks), inyección de paquetes huérfanos.

```bash
# 1. Desarrollo: cotas de versión en pyproject.toml (ver estándar #4)

# 2. Releases y CI/CD: lockfile estricto con hashes criptográficos SHA-256
uv lock
# — O —
pip-compile requirements.in --generate-hashes --output-file requirements-lock.txt

# 3. Auditoría de seguridad obligatoria antes de merge
pip-audit --strict
```

**Política:** Ninguna release se publica ante vulnerabilidades conocidas de severidad HIGH o CRITICAL.

---

### #13 — Manejo Seguro de Errores & Fallos Controlados (CWE-209)

**Disparador Técnico:** Bloques `try/except`, respuestas HTTP, formateo de logs y procesamiento de streams masivos.  
**Vector / CWE:** CWE-209 (Generation of Error Message Containing Sensitive Information).

```python
import logging, traceback

logger = logging.getLogger(__name__)

# ❌ INCORRECTO — volcar tracebacks con rutas locales o variables hacia el usuario
# return {"error": str(e), "traceback": traceback.format_exc()}

# ✅ CORRECTO — mensaje genérico al exterior + log sanitizado local
def handle_transaction(item_id: str, raw_payload: str):
    try:
        process(raw_payload)
    except Exception:
        # Traceback sanitizado al log local
        sanitized = traceback.format_exc().replace(str(raw_payload), "[REDACTED_PAYLOAD]")
        logger.error("Error procesando item_id=%s: %s", item_id, sanitized)
        # Mensaje genérico hacia el cliente
        return {"error": "Error interno procesando la solicitud"}

# ✅ CORRECTO — fail-open controlado en procesamiento de streams masivos
def process_stream(records: list):
    valid_results = []
    for rec in records:
        try:
            valid_results.append(parse_record(rec))
        except Exception:
            logger.warning("Registro corrupto omitido — el pipeline continúa")
    return valid_results
```

---

### #14 — Blindaje contra SSRF en Webhooks & Nodos HTTP (CWE-918)

**Disparador Técnico:** Módulos `httpx`, `requests`, `urllib` o workflows n8n que realizan llamadas HTTP salientes a URLs dinámicas o proporcionadas por usuarios.  
**Vector / CWE:** CWE-918 (Server-Side Request Forgery).

```python
import ipaddress
import socket
from urllib.parse import urlparse

# ❌ INCORRECTO — llamar a URLs arbitrarias sin validación de red
# response = httpx.get(user_provided_url)

# ✅ CORRECTO — Denylist estricta de IPs privadas, loopback y metadata cloud
PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.169.254/32"), # Cloud metadata
    ipaddress.ip_network("::1/128"),
]

def validate_safe_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Esquema no permitido: {parsed.scheme}")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL sin hostname válido")
        
    # Resolver DNS previo para evitar bypass por DNS Rebinding
    ip_str = socket.gethostbyname(hostname)
    ip_obj = ipaddress.ip_address(ip_str)
    
    for net in PRIVATE_NETWORKS:
        if ip_obj in net:
            raise PermissionError(f"SSRF bloqueado: destino privado prohibido ({ip_str})")
            
    return url
```

---

### #15 — Mitigación de Prompt Injection & AST Guardrails (OWASP LLM01 / CWE-20)

**Disparador Técnico:** Integraciones con LLMs, frameworks de agentes (`langgraph`, `langchain`), generación de código o procesamiento de lenguaje natural no estructurado.  
**Vector / CWE:** OWASP LLM01 (Prompt Injection), CWE-20 (Improper Input Validation).

```python
from pydantic import BaseModel, Field, ConfigDict
import re

# ❌ INCORRECTO — confiar ciegamente en la respuesta del LLM o pasar texto crudo a eval/exec
# result = eval(llm_response_text)

# ✅ CORRECTO — Esquemas inmutables Pydantic v2 con rechazo de campos extra
class StructuredAgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    status: str = Field(..., pattern=r"^(SUCCESS|FAILED|RETRY)$")
    reasoning: str = Field(..., max_length=2000)
    suggested_commands: list[str] = Field(default_factory=list, max_length=5)

# ✅ CORRECTO — Verificación determinista AST previa a cualquier ejecución
def sanitize_agent_command(cmd: str) -> str:
    forbidden_tokens = ["rm -rf", "drop table", "chmod 777", "eval(", "os.system", ";", "&&", "|"]
    for token in forbidden_tokens:
        if token in cmd.lower():
            raise SecurityError(f"Token malicioso detectado en comando del agente: {token}")
    return cmd.strip()
```

---

### #16 — Contención de Agencia Excesiva & Human-in-the-Loop (OWASP LLM06 / CWE-250)

**Disparador Técnico:** Agentes con acceso a herramientas que mutan el estado del sistema, despliegan código, borran datos o ejecutan comandos del sistema operativo.  
**Vector / CWE:** OWASP LLM06 (Excessive Agency), CWE-250 (Execution with Unnecessary Privileges).

```python
from typing import Dict, Any

# ✅ CORRECTO — Punto de interrupción obligatorio (Human-in-the-loop)
MUTABLE_ACTIONS = {"rollback", "apply_patch", "restart_daemon", "delete_file"}

def execute_agent_action(action_name: str, params: Dict[str, Any], user_confirmed: bool = False) -> Dict[str, Any]:
    if action_name in MUTABLE_ACTIONS:
        if not user_confirmed:
            # Pausar y requerir confirmación explícita (interrupt_before en LangGraph)
            return {
                "status": "WAITING_HUMAN_CONFIRMATION",
                "action": action_name,
                "params": params,
                "prompt": f"¿Confirma la ejecución de la acción destructiva '{action_name}'?"
            }
    # Ejecutar en sandbox controlado
    return {"status": "EXECUTED", "action": action_name}
```

---

### #17 — Prevención de DoS en Grafos Cíclicos & Bounding (OWASP LLM10 / CWE-400)

**Disparador Técnico:** Grafos de estado (`StateGraph`), bucles de reintento `while`, agentes auto-reflexivos y pipelines de streaming.  
**Vector / CWE:** OWASP LLM10 (Unbounded Consumption), CWE-400 (Uncontrolled Resource Consumption).

```python
import asyncio

# ✅ CORRECTO — Límites duros de recursión y timeouts en grafos de agentes
MAX_GRAPH_ITERATIONS = 4
EXECUTION_TIMEOUT_SECONDS = 30.0

async def run_bounded_agent_graph(graph_app, initial_state: dict):
    # recursion_limit forzado a nivel de compilación/ejecución
    config = {"recursion_limit": MAX_GRAPH_ITERATIONS}
    
    try:
        async with asyncio.timeout(EXECUTION_TIMEOUT_SECONDS):
            final_state = await graph_app.ainvoke(initial_state, config=config)
            return final_state
    except TimeoutError:
        raise TimeoutError(f"Grafo de agentes excedió el tiempo límite seguro ({EXECUTION_TIMEOUT_SECONDS}s)")
```

---

## 3️⃣ Tests & Gates — Flujo de Aprobación & Matriz por Arquetipos

> **Regla cardinal:** Ningún hito de desarrollo ni PR avanza con un gate fallido.

### ⚡ Comando Maestro de Validación Continua

Ejecutar **obligatoriamente** tras cada cambio o antes de cualquier commit:

```bash
pytest -v && bandit -r . -ll && gitleaks detect
```

Los tres comandos deben retornar **código de salida 0**. Cualquier fallo detiene la ejecución.

---

### 📊 Matriz Universal de Gates por Arquetipo de Software

| Arquetipo de Software | Tests Unitarios | Cobertura Mínima | Suite SAST & Secrets | Requisito de Benchmark |
|---|:---:|:---:|:---:|:---:|
| **Motores Criptográficos & Integridad** | $\ge 45$ tests | $\ge 90\%$ | Bandit + Gitleaks + `compare_digest` | Rendimiento criptográfico (`hash/s`, tamper-check) |
| **Modelos ML & Detección Estadística** | $\ge 40$ tests | $\ge 90\%$ | Bandit + Gitleaks + Deserialización segura | Latencia de inferencia en CPU (`ms/batch`) |
| **Pipelines ETL & Timelines Forenses** | $\ge 40$ tests | $\ge 90\%$ | Bandit + Gitleaks + ReDoS audit | Consumo de RAM acotado en streaming (`<50 MB`) |
| **Inspección Binaria, Tar/Zip & Carvers** | $\ge 45$ tests | $\ge 90\%$ | Bandit + Tar-bomb test + Commonpath | Velocidad de escaneo (`MB/s`) |
| **Grafos & Análisis de Vínculos** | $\ge 35$ tests | $\ge 90\%$ | Bandit + Sanitización PII | Rendimiento en CPU (`aristas/s`) |
| **Runners de CI/CD, Sandboxes & DAGs** | $\ge 45$ tests | $\ge 90\%$ | Bandit + `safe_load` + `shell=False` | Detección de ciclos y timeouts de procesos |
| **Demonios de Sistema & SRE Watchdogs** | $\ge 40$ tests | $\ge 90\%$ | Bandit + Verificación `geteuid()` | Overhead de CPU/RAM (`<0.1% CPU`) |
| **Proxies L7, Rate Limiters & Red** | $\ge 45$ asíncronos | $\ge 90\%$ | Bandit + DoS payload limit + TLS audit | Throughput de tráfico (`req/s`, latencia ms) |
| **Auditoría GitOps & Drift Detectors** | $\ge 40$ tests | $\ge 90\%$ | Bandit + Verificación estricta Read-Only | Idempotencia demostrada por test suite |
| **Orquestadores de DR & Backup Seguro** | $\ge 45$ E2E | $\ge 90\%$ | Bandit + File locks + Cleanup garantizado | Tiempo de ciclo E2E (Backup $\to$ Hash match) |
| **Exporters de Métricas & Monitoreo** | $\ge 40$ tests | $\ge 90\%$ | Bandit + OpenMetrics conformance | Capacidad de scraping concurrente (`req/s`) |
| **Streaming Daemons & Procesadores** | $\ge 45$ tests | $\ge 90\%$ | Bandit + Buffer durable + PII mask | Throughput de ingestión (`eventos/s`) |
| **Chaos Engineering & Inyectores** | $\ge 40$ tests | $\ge 90\%$ | Bandit + Dead-man switch + Whitelist | Rollback atómico garantizado ante SIGKILL |
| **Sistemas Cuantitativos & SLO Engines** | $\ge 45$ tests | $\ge 90\%$ | Bandit + Pydantic schema validation | Precisión matemática Multi-Window / Burn-rate |
| **Distributed Tracing SDKs & Profilers** | $\ge 45$ asíncronos | $\ge 90\%$ | Bandit + W3C TraceContext conformance | Overhead por request (`<1 ms`) |

### Cobertura de Código

```bash
pytest --cov=. --cov-report=term-missing --cov-fail-under=90
```

### 🚫 Política Anti Reward-Hacking (Regla Dura)

```
PROHIBIDO en cualquier circunstancia:
  ✗ Borrar tests para hacer pasar el gate de cobertura
  ✗ Saltar tests con @pytest.mark.skip sin justificación técnica documentada
  ✗ Debilitar assertions (assert True, assert len(x) >= 0)
  ✗ Mockear el código bajo test en lugar de las dependencias externas
  ✗ Hardcodear valores en benchmarks/resultados.json para simular métricas
```

---

## 4️⃣ Gold Standard de Release — Checklist Pre-Push

> Antes de hacer `git push` a un repositorio público o release, verificar **OBLIGATORIAMENTE** los 7 puntos:

- [ ] **CI/CD Activo:** Workflow `.github/workflows/security-scan.yml` ejecutando Bandit, pip-audit y Gitleaks en cada push/PR.
- [ ] **Commits Firmados GPG:** `git config commit.gpgsign true` con badge *Verified* en GitHub.
- [ ] **SBOM Publicado:** `sbom.json` (CycloneDX) adjunto en los releases.
- [ ] **`SECURITY.md` en Raíz:** Presente en la raíz del repositorio siguiendo la plantilla oficial.
- [ ] **Escaneo de Contenedores:** `trivy image --severity HIGH,CRITICAL --exit-code 1 <img>` (si incluye Dockerfile).
- [ ] **Dependabot Habilitado:** `.github/dependabot.yml` activo con revisiones semanales.
- [ ] **README con Insignias:** Badges de Tests, Security Scan, CodeQL y SBOM visibles.

---

## 5️⃣ Reglas de Oro — OWASP ASVS / NIST SSDF / CWE Top 25

> Disposiciones adicionales vinculantes por **Disparador de Arquitectura**:

| Fuente Normativa | Disposición Adicional Vinculante | Disparador de Arquitectura / Ámbito |
|---|---|---|
| **OWASP ASVS V2** | Toda validación ocurre en el sistema confiable; validación sintáctica y semántica obligatoria. | **General:** Toda entrada de datos externa, usuario o red |
| **OWASP ASVS (Comunicaciones)** | TLS 1.2+ obligatorio; minimización de datos y política de retención y purga definidas. | **Red:** Componentes expuestos a red, APIs, proxies y sockets |
| **OWASP ASVS (DB Security)** | Consultas SQLite 100% parametrizadas; mínimo privilegio (sin DDL en runtime salvo migración). | **Persistencia:** Bases de datos relacionales y almacenamiento SQL |
| **OWASP Secure Coding** | Prohibido `pickle.load()` sobre datos no confiables; context managers obligatorios para recursos. | **Serialización:** Modelos ML, persistencia de estado y caché |
| **OWASP ASVS (File Security)** | Validación obligatoria por magic bytes (la extensión/MIME declarada jamás es confiable). | **Archivos:** Ingesta de archivos, file-carving y parsers binarios |
| **NIST SSDF (PW/PD)** | Hardening por defecto: configuraciones inseguras requieren opt-in; variables de entorno para config. | **Configuración:** Todos los proyectos |
| **SRE Golden Signals** | Alertas de anomalías de autenticación, saturación y uso anómalo de privilegios. | **Observabilidad:** Métricas, exporters y motores de monitoreo |
| **CWE-502 (Deserialización)** | Prohibido deserializar formatos dinámicos sin schema estricto y tipado explícito. | **Declarativo:** Parsers YAML, JSON-Lines y runners de pipelines |
| **CWE-400 (Anti-DoS)** | Bucles de procesamiento con cota máxima de iteraciones, tamaño de bloque y tiempo de CPU. | **Streaming & Tráfico:** Proxies, pipelines y procesadores de logs |
| **SLSA L2 (Cadena de Suministro)** | Build scriptado, reproducible y lockfile de dependencias fijado con hashes SHA-256. | **Supply Chain:** Todos los proyectos |

---

## 📎 Apéndice — Herramientas de Verificación (Instalación Rápida)

```bash
# Instalación en entorno de desarrollo
pip install bandit pip-audit cyclonedx-bom mypy pytest pytest-cov

# gitleaks
curl -sSfL https://raw.githubusercontent.com/gitleaks/gitleaks/main/scripts/install.sh | sh

# uv (gestor de paquetes con lockfile nativo)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

*Documento canónico de seguridad · Aplicar a todos los repositorios y desarrollos de software del workspace.*
