# db_manager.py – Gestor de base de datos SQLite para PrintMoney
# Maneja la creación del esquema, conexión y operaciones CRUD principales

import sqlite3
import os
import json
from contextlib import contextmanager
from datetime import date

import sys

# Ruta de la base de datos
if getattr(sys, 'frozen', False):
    # Si es un ejecutable PyInstaller, usar la carpeta donde está el .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)

DB_PATH = os.path.join(BASE_DIR, "data", "printmoney.db")
BACKUP_DIR = os.path.join(BASE_DIR, "data", "backups")

# Número máximo de backups diarios que se conservan (los manuales nunca se purgan)
MAX_BACKUPS = 30


@contextmanager
def obtener_conexion():
    """Context manager que entrega una conexión SQLite y la cierra siempre.

    Antes de este cambio cada función hacía `conn = obtener_conexion()` y un
    `conn.close()` al final: si cualquier `execute` lanzaba una excepción, la
    conexión quedaba abierta para siempre (fuga de file descriptors) y la
    transacción sin confirmar. Con `with` el commit/rollback/close están
    garantizados.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ruta_backups() -> str:
    """Devuelve la ruta absoluta de la carpeta de backups respetando config.json."""
    carpeta = ""
    try:
        with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
            carpeta = (json.load(f) or {}).get("carpeta_backups") or ""
    except Exception:
        carpeta = ""
    if not carpeta:
        carpeta = "data/backups"
    if not os.path.isabs(carpeta):
        carpeta = os.path.join(BASE_DIR, carpeta)
    return carpeta


def _num(datos: dict, clave: str, defecto=0.0):
    """Lee un número de un dict devolviendo el defecto si falta o es None."""
    valor = datos.get(clave, defecto)
    return defecto if valor is None else valor


def inicializar_db():
    """Crea todas las tablas e índices si no existen. Se llama en el arranque."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(ruta_backups(), exist_ok=True)

    with obtener_conexion() as conn:
        cursor = conn.cursor()

        # --- Tabla de clientes ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT,
                telefono TEXT,
                direccion TEXT,
                notas TEXT,
                fecha_registro TEXT DEFAULT (date('now'))
            )
        """)

        # --- Tabla de impresoras (preparada para futuro) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS impresoras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                tarifa_por_hora REAL DEFAULT 5.0,
                activa INTEGER DEFAULT 1
            )
        """)

        # --- Tabla de inventario de filamentos ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS filamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                material TEXT DEFAULT 'PLA',
                color TEXT,
                gramos_restantes REAL DEFAULT 0,
                precio_por_kg REAL DEFAULT 0,
                umbral_bajo REAL DEFAULT 100,
                proveedor TEXT,
                notas TEXT
            )
        """)

        # --- Tabla de pedidos ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT DEFAULT (date('now')),
                cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
                descripcion TEXT,
                filamento_id INTEGER REFERENCES filamentos(id) ON DELETE SET NULL,
                gramos_usados REAL DEFAULT 0,
                horas_impresion REAL DEFAULT 0,
                costo_material REAL DEFAULT 0,
                costo_tiempo REAL DEFAULT 0,
                costo_envio REAL DEFAULT 0,
                precio_venta REAL DEFAULT 0,
                ganancia REAL DEFAULT 0,
                margen_porcentaje REAL DEFAULT 0,
                fecha_entrega TEXT,
                estado TEXT DEFAULT 'pendiente',
                notas TEXT,
                factura_generada INTEGER DEFAULT 0
            )
        """)

        # --- Tabla de categorías de gastos ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorias_gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            )
        """)

        # Insertar categorías predeterminadas si no existen
        categorias_default = ["Filamento", "Marketing", "Envío", "Mantenimiento", "Otros"]
        for cat in categorias_default:
            cursor.execute("INSERT OR IGNORE INTO categorias_gastos (nombre) VALUES (?)", (cat,))

        # --- Tabla de gastos ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT DEFAULT (date('now')),
                categoria_id INTEGER REFERENCES categorias_gastos(id),
                descripcion TEXT,
                monto REAL DEFAULT 0,
                recurrente INTEGER DEFAULT 0,
                frecuencia TEXT DEFAULT 'mensual',
                notas TEXT
            )
        """)

        # --- Historial de consumo de filamento ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial_filamento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filamento_id INTEGER REFERENCES filamentos(id) ON DELETE CASCADE,
                pedido_id INTEGER REFERENCES pedidos(id) ON DELETE SET NULL,
                gramos_consumidos REAL DEFAULT 0,
                fecha TEXT DEFAULT (date('now'))
            )
        """)

        # --- Catálogo de productos ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalogo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                filamento_base_id INTEGER REFERENCES filamentos(id) ON DELETE SET NULL,
                gramos_estimados REAL DEFAULT 0,
                horas_estimadas REAL DEFAULT 0,
                precio_sugerido REAL DEFAULT 0
            )
        """)

        # --- Índices ---
        # Los reportes filtran y agregan por fecha y estado; sin índices cada
        # informe recorría la tabla entera en cada consulta.
        for sql in (
            "CREATE INDEX IF NOT EXISTS idx_pedidos_fecha ON pedidos(fecha)",
            "CREATE INDEX IF NOT EXISTS idx_pedidos_cliente ON pedidos(cliente_id)",
            "CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON pedidos(estado)",
            "CREATE INDEX IF NOT EXISTS idx_pedidos_filamento ON pedidos(filamento_id)",
            "CREATE INDEX IF NOT EXISTS idx_gastos_fecha ON gastos(fecha)",
            "CREATE INDEX IF NOT EXISTS idx_gastos_categoria ON gastos(categoria_id)",
            "CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes(nombre)",
            "CREATE INDEX IF NOT EXISTS idx_historial_pedido ON historial_filamento(pedido_id)",
            "CREATE INDEX IF NOT EXISTS idx_historial_filamento ON historial_filamento(filamento_id)",
        ):
            cursor.execute(sql)


def _copiar_db_segura(ruta_destino: str):
    """Copia la base de datos usando la API de backup de SQLite.

    `shutil.copy2` sobre un fichero SQLite abierto puede copiar una imagen
    inconsistente si hay escrituras en curso (páginas a medio escribir). La API
    `Connection.backup()` garantiza una copia consistente aunque la app tenga
    la base de datos abierta.
    """
    origen = sqlite3.connect(DB_PATH)
    try:
        destino = sqlite3.connect(ruta_destino)
        try:
            origen.backup(destino)
        finally:
            destino.close()
    finally:
        origen.close()


def _purgar_backups_viejos(backup_dir: str, maximo: int = MAX_BACKUPS):
    """Elimina los backups diarios más antiguos, conservando los `maximo` últimos.

    Los backups manuales (`backup_manual_*`) nunca se tocan.
    """
    try:
        diarios = []
        for nombre in os.listdir(backup_dir):
            if not (nombre.startswith("backup_") and nombre.endswith(".db")):
                continue
            if nombre.startswith("backup_manual_"):
                continue
            ruta = os.path.join(backup_dir, nombre)
            if os.path.isfile(ruta):
                diarios.append((nombre, ruta))
        diarios.sort()  # orden lexicográfico = orden cronológico por fecha
        if len(diarios) > maximo:
            for _, ruta in diarios[:-maximo]:
                try:
                    os.remove(ruta)
                except OSError:
                    pass
    except OSError:
        pass


def hacer_backup_diario():
    """Crea un backup de la base de datos con fecha actual si no existe ya."""
    if not os.path.exists(DB_PATH):
        return False
    backup_dir = ruta_backups()
    os.makedirs(backup_dir, exist_ok=True)
    nombre_backup = f"backup_{date.today().strftime('%Y-%m-%d')}.db"
    ruta_backup = os.path.join(backup_dir, nombre_backup)
    if os.path.exists(ruta_backup):
        return False  # Ya existía
    try:
        _copiar_db_segura(ruta_backup)
    except Exception:
        return False
    _purgar_backups_viejos(backup_dir)
    return True  # Backup realizado


def hacer_backup_manual() -> str:
    """Crea un backup manual con fecha y devuelve su ruta."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(DB_PATH)
    backup_dir = ruta_backups()
    os.makedirs(backup_dir, exist_ok=True)
    nombre = f"backup_manual_{date.today().strftime('%Y-%m-%d')}.db"
    ruta = os.path.join(backup_dir, nombre)
    _copiar_db_segura(ruta)
    return ruta


# ======================== CLIENTES ========================

def agregar_cliente(nombre, email="", telefono="", direccion="", notas=""):
    """Inserta un nuevo cliente en la base de datos."""
    with obtener_conexion() as conn:
        conn.execute(
            "INSERT INTO clientes (nombre, email, telefono, direccion, notas) VALUES (?,?,?,?,?)",
            (nombre, email, telefono, direccion, notas)
        )


def obtener_clientes():
    """Retorna lista de todos los clientes."""
    with obtener_conexion() as conn:
        rows = conn.execute("SELECT * FROM clientes ORDER BY nombre").fetchall()
    return [dict(r) for r in rows]


def actualizar_cliente(id, nombre, email, telefono, direccion, notas):
    """Actualiza los datos de un cliente existente."""
    with obtener_conexion() as conn:
        conn.execute(
            "UPDATE clientes SET nombre=?, email=?, telefono=?, direccion=?, notas=? WHERE id=?",
            (nombre, email, telefono, direccion, notas, id)
        )


def eliminar_cliente(id):
    """Elimina un cliente por ID."""
    with obtener_conexion() as conn:
        conn.execute("DELETE FROM clientes WHERE id=?", (id,))


# ======================== FILAMENTOS ========================

def agregar_filamento(nombre, material, color, gramos, precio_kg, umbral, proveedor="", notas=""):
    """Agrega un nuevo filamento al inventario."""
    with obtener_conexion() as conn:
        conn.execute(
            """INSERT INTO filamentos (nombre, material, color, gramos_restantes, precio_por_kg, umbral_bajo, proveedor, notas)
               VALUES (?,?,?,?,?,?,?,?)""",
            (nombre, material, color, gramos, precio_kg, umbral, proveedor, notas)
        )


def obtener_filamentos():
    """Retorna todos los filamentos del inventario."""
    with obtener_conexion() as conn:
        rows = conn.execute("SELECT * FROM filamentos ORDER BY nombre").fetchall()
    return [dict(r) for r in rows]


def actualizar_filamento(id, nombre, material, color, gramos, precio_kg, umbral, proveedor, notas):
    """Actualiza los datos de un filamento."""
    with obtener_conexion() as conn:
        conn.execute(
            """UPDATE filamentos SET nombre=?, material=?, color=?, gramos_restantes=?,
               precio_por_kg=?, umbral_bajo=?, proveedor=?, notas=? WHERE id=?""",
            (nombre, material, color, gramos, precio_kg, umbral, proveedor, notas, id)
        )


def eliminar_filamento(id):
    """Elimina un filamento del inventario."""
    with obtener_conexion() as conn:
        conn.execute("DELETE FROM filamentos WHERE id=?", (id,))


def obtener_filamentos_bajo_umbral():
    """Retorna filamentos cuyo stock está por debajo del umbral configurado."""
    with obtener_conexion() as conn:
        rows = conn.execute(
            "SELECT * FROM filamentos WHERE gramos_restantes < umbral_bajo"
        ).fetchall()
    return [dict(r) for r in rows]


# ======================== PEDIDOS ========================

def _sincronizar_consumo(conn, pedido_id, filamento_previo, gramos_previos,
                          filamento_nuevo, gramos_nuevos):
    """Mantiene el inventario y el historial alineados con un pedido.

    Devuelve al inventario el consumo anterior (si lo había), retira la fila
    del historial de ese pedido y descuenta el consumo nuevo. Se usa al crear,
    editar y borrar un pedido, de modo que el stock nunca queda desincronizado
    del histórico.
    """
    if filamento_previo and gramos_previos:
        conn.execute(
            "UPDATE filamentos SET gramos_restantes = gramos_restantes + ? WHERE id=?",
            (gramos_previos, filamento_previo)
        )
    if pedido_id:
        conn.execute("DELETE FROM historial_filamento WHERE pedido_id=?", (pedido_id,))
    if filamento_nuevo and gramos_nuevos:
        conn.execute(
            "UPDATE filamentos SET gramos_restantes = MAX(0, gramos_restantes - ?) WHERE id=?",
            (gramos_nuevos, filamento_nuevo)
        )
        conn.execute(
            "INSERT INTO historial_filamento (filamento_id, pedido_id, gramos_consumidos) VALUES (?,?,?)",
            (filamento_nuevo, pedido_id, gramos_nuevos)
        )


def agregar_pedido(datos: dict):
    """
    Inserta un nuevo pedido y descuenta gramos del inventario automáticamente.
    datos: dict con todos los campos del pedido.
    """
    precio_venta = _num(datos, "precio_venta", 0)
    costo_total = (_num(datos, "costo_material") + _num(datos, "costo_tiempo")
                   + _num(datos, "costo_envio"))
    ganancia = precio_venta - costo_total
    margen = (ganancia / precio_venta * 100) if precio_venta > 0 else 0

    filamento_id = datos.get("filamento_id")
    gramos_usados = _num(datos, "gramos_usados", 0)

    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pedidos (fecha, cliente_id, descripcion, filamento_id, gramos_usados,
                horas_impresion, costo_material, costo_tiempo, costo_envio, precio_venta,
                ganancia, margen_porcentaje, fecha_entrega, estado, notas)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datos.get("fecha") or str(date.today()),
            datos.get("cliente_id"),
            datos.get("descripcion", ""),
            filamento_id,
            gramos_usados,
            _num(datos, "horas_impresion", 0),
            _num(datos, "costo_material", 0),
            _num(datos, "costo_tiempo", 0),
            _num(datos, "costo_envio", 0),
            precio_venta,
            ganancia,
            margen,
            datos.get("fecha_entrega", ""),
            datos.get("estado") or "pendiente",
            datos.get("notas", "")
        ))
        pedido_id = cursor.lastrowid

        # Descontar gramos del inventario si hay filamento asignado
        _sincronizar_consumo(conn, pedido_id, None, 0, filamento_id, gramos_usados)

    return pedido_id


def _filtro_texto_sql(texto, params):
    """Añade a `params` el patrón LIKE de búsqueda de texto libre."""
    if not texto or not texto.strip():
        return None
    texto = texto.strip()
    # Escapar los comodines de LIKE para que '%' y '_' se busquen literales
    patron = "%" + texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    condiciones = ["c.nombre LIKE ? ESCAPE '\\'", "p.descripcion LIKE ? ESCAPE '\\'"]
    params.extend([patron, patron])
    if texto.isdigit():
        condiciones.append("p.id = ?")
        params.append(int(texto))
    return "(" + " OR ".join(condiciones) + ")"


def obtener_pedidos(filtro_cliente_id=None, filtro_estado=None, filtro_fecha_desde=None,
                     filtro_fecha_hasta=None, filtro_texto=None, limite=None, offset=0):
    """Retorna pedidos con joins a clientes y filamentos, con filtros opcionales.

    `filtro_texto` busca en el nombre del cliente y en la descripción (y en el
    ID si es numérico). Se resuelve en SQL para no traer toda la tabla a Python.
    """
    query = """
        SELECT p.*, c.nombre AS cliente_nombre, f.nombre AS filamento_nombre
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        LEFT JOIN filamentos f ON p.filamento_id = f.id
        WHERE 1=1
    """
    params = []
    if filtro_cliente_id:
        query += " AND p.cliente_id = ?"
        params.append(filtro_cliente_id)
    if filtro_estado:
        query += " AND p.estado = ?"
        params.append(filtro_estado)
    if filtro_fecha_desde:
        query += " AND p.fecha >= ?"
        params.append(filtro_fecha_desde)
    if filtro_fecha_hasta:
        query += " AND p.fecha <= ?"
        params.append(filtro_fecha_hasta)
    cond_texto = _filtro_texto_sql(filtro_texto, params)
    if cond_texto:
        query += " AND " + cond_texto
    query += " ORDER BY p.fecha DESC, p.id DESC"
    if limite is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limite, offset])

    with obtener_conexion() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def contar_pedidos(filtro_cliente_id=None, filtro_estado=None, filtro_fecha_desde=None,
                   filtro_fecha_hasta=None, filtro_texto=None):
    """Cuenta pedidos que cumplen los mismos filtros que `obtener_pedidos`."""
    query = """
        SELECT COUNT(*) as total
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE 1=1
    """
    params = []
    if filtro_cliente_id:
        query += " AND p.cliente_id = ?"
        params.append(filtro_cliente_id)
    if filtro_estado:
        query += " AND p.estado = ?"
        params.append(filtro_estado)
    if filtro_fecha_desde:
        query += " AND p.fecha >= ?"
        params.append(filtro_fecha_desde)
    if filtro_fecha_hasta:
        query += " AND p.fecha <= ?"
        params.append(filtro_fecha_hasta)
    cond_texto = _filtro_texto_sql(filtro_texto, params)
    if cond_texto:
        query += " AND " + cond_texto

    with obtener_conexion() as conn:
        row = conn.execute(query, params).fetchone()
    return row["total"]


def obtener_pedido_por_id(id):
    """Retorna un pedido con los datos de cliente y filamento, o None."""
    with obtener_conexion() as conn:
        row = conn.execute("""
            SELECT p.*, c.nombre AS cliente_nombre, f.nombre AS filamento_nombre
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN filamentos f ON p.filamento_id = f.id
            WHERE p.id = ?
        """, (id,)).fetchone()
    return dict(row) if row else None


def actualizar_pedido(id, datos: dict):
    """Actualiza un pedido existente y reajusta el inventario de filamento."""
    precio_venta = _num(datos, "precio_venta", 0)
    costo_total = (_num(datos, "costo_material") + _num(datos, "costo_tiempo")
                   + _num(datos, "costo_envio"))
    ganancia = precio_venta - costo_total
    margen = (ganancia / precio_venta * 100) if precio_venta > 0 else 0

    filamento_id = datos.get("filamento_id")
    gramos_usados = _num(datos, "gramos_usados", 0)

    with obtener_conexion() as conn:
        previo = conn.execute(
            "SELECT filamento_id, gramos_usados FROM pedidos WHERE id=?", (id,)
        ).fetchone()

        conn.execute("""
            UPDATE pedidos SET fecha=?, cliente_id=?, descripcion=?, filamento_id=?, gramos_usados=?,
                horas_impresion=?, costo_material=?, costo_tiempo=?, costo_envio=?, precio_venta=?,
                ganancia=?, margen_porcentaje=?, fecha_entrega=?, estado=?, notas=?
            WHERE id=?
        """, (
            datos.get("fecha") or str(date.today()),
            datos.get("cliente_id"),
            datos.get("descripcion", ""),
            filamento_id,
            gramos_usados,
            _num(datos, "horas_impresion", 0),
            _num(datos, "costo_material", 0),
            _num(datos, "costo_tiempo", 0),
            _num(datos, "costo_envio", 0),
            precio_venta,
            ganancia,
            margen,
            datos.get("fecha_entrega", ""),
            datos.get("estado") or "pendiente",
            datos.get("notas", ""),
            id
        ))

        # Devolver el consumo anterior al inventario y descontar el nuevo
        _sincronizar_consumo(
            conn, id,
            previo["filamento_id"] if previo else None,
            (previo["gramos_usados"] or 0) if previo else 0,
            filamento_id,
            gramos_usados,
        )


def eliminar_pedido(id):
    """Elimina un pedido por ID devolviendo al inventario el filamento consumido."""
    with obtener_conexion() as conn:
        previo = conn.execute(
            "SELECT filamento_id, gramos_usados FROM pedidos WHERE id=?", (id,)
        ).fetchone()
        # El historial debe borrarse ANTES que el pedido: la FK es ON DELETE
        # SET NULL, así que al borrar el pedido el pedido_id pasa a NULL y el
        # registro fantasma quedaría sin poder localizarse.
        if previo:
            _sincronizar_consumo(
                conn, id,
                previo["filamento_id"],
                previo["gramos_usados"] or 0,
                None, 0,
            )
        conn.execute("DELETE FROM pedidos WHERE id=?", (id,))


def marcar_factura_generada(pedido_id):
    """Marca un pedido como factura generada."""
    with obtener_conexion() as conn:
        conn.execute("UPDATE pedidos SET factura_generada=1 WHERE id=?", (pedido_id,))


# ======================== GASTOS ========================

def obtener_categorias_gastos():
    """Retorna todas las categorías de gastos."""
    with obtener_conexion() as conn:
        rows = conn.execute("SELECT * FROM categorias_gastos ORDER BY nombre").fetchall()
    return [dict(r) for r in rows]


def agregar_categoria_gasto(nombre):
    """Agrega una nueva categoría de gasto."""
    with obtener_conexion() as conn:
        conn.execute("INSERT OR IGNORE INTO categorias_gastos (nombre) VALUES (?)", (nombre,))


def agregar_gasto(fecha, categoria_id, descripcion, monto, recurrente=0, frecuencia="mensual", notas=""):
    """Inserta un nuevo gasto."""
    with obtener_conexion() as conn:
        conn.execute(
            "INSERT INTO gastos (fecha, categoria_id, descripcion, monto, recurrente, frecuencia, notas) VALUES (?,?,?,?,?,?,?)",
            (fecha, categoria_id, descripcion, monto, recurrente, frecuencia, notas)
        )


def actualizar_gasto(id, fecha, categoria_id, descripcion, monto, recurrente=0,
                      frecuencia="mensual", notas=""):
    """Actualiza un gasto existente. Antes solo se podían crear o borrar."""
    with obtener_conexion() as conn:
        conn.execute(
            "UPDATE gastos SET fecha=?, categoria_id=?, descripcion=?, monto=?, recurrente=?, frecuencia=?, notas=? WHERE id=?",
            (fecha, categoria_id, descripcion, monto, recurrente, frecuencia, notas, id)
        )


def obtener_gastos(fecha_desde=None, fecha_hasta=None):
    """Retorna gastos con nombre de categoría, con filtros opcionales."""
    query = """
        SELECT g.*, c.nombre AS categoria_nombre
        FROM gastos g
        LEFT JOIN categorias_gastos c ON g.categoria_id = c.id
        WHERE 1=1
    """
    params = []
    if fecha_desde:
        query += " AND g.fecha >= ?"
        params.append(fecha_desde)
    if fecha_hasta:
        query += " AND g.fecha <= ?"
        params.append(fecha_hasta)
    query += " ORDER BY g.fecha DESC, g.id DESC"

    with obtener_conexion() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def eliminar_gasto(id):
    """Elimina un gasto por ID."""
    with obtener_conexion() as conn:
        conn.execute("DELETE FROM gastos WHERE id=?", (id,))


# ======================== REPORTES / ESTADÍSTICAS ========================

# Los pedidos cancelados no son ventas: se excluyen de todos los cálculos
# de ingresos, ganancia y número de pedidos.
_COND_ACTIVO = "estado != 'cancelado'"


def obtener_estadisticas_mes(year, month):
    """Retorna ingresos, gastos y ganancia neta de un mes específico."""
    fecha_inicio = f"{year}-{month:02d}-01"
    # Primer día del mes siguiente (exclusivo)
    if month == 12:
        fecha_fin = f"{year+1}-01-01"
    else:
        fecha_fin = f"{year}-{month+1:02d}-01"

    with obtener_conexion() as conn:
        r = conn.execute(
            f"""SELECT COALESCE(SUM(precio_venta),0) as total FROM pedidos
                WHERE fecha >= ? AND fecha < ? AND {_COND_ACTIVO}""",
            (fecha_inicio, fecha_fin)
        ).fetchone()
        ingresos = r["total"]

        r = conn.execute(
            "SELECT COALESCE(SUM(monto),0) as total FROM gastos WHERE fecha >= ? AND fecha < ?",
            (fecha_inicio, fecha_fin)
        ).fetchone()
        gastos = r["total"]

        r = conn.execute(
            f"""SELECT COUNT(*) as total FROM pedidos
                WHERE fecha >= ? AND fecha < ? AND {_COND_ACTIVO}""",
            (fecha_inicio, fecha_fin)
        ).fetchone()
        num_pedidos = r["total"]

        r = conn.execute(
            f"""SELECT COALESCE(SUM(ganancia),0) as total FROM pedidos
                WHERE fecha >= ? AND fecha < ? AND {_COND_ACTIVO}""",
            (fecha_inicio, fecha_fin)
        ).fetchone()
        ganancia_pedidos = r["total"]

        # Pedidos pendientes (sin importar mes)
        r = conn.execute(
            "SELECT COUNT(*) as total FROM pedidos WHERE estado='pendiente'"
        ).fetchone()
        pendientes = r["total"]

    return {
        "ingresos": ingresos,
        "gastos": gastos,
        "ganancia_neta": ganancia_pedidos - gastos,
        "margen": (ganancia_pedidos / ingresos * 100) if ingresos > 0 else 0,
        "num_pedidos": num_pedidos,
        "pendientes": pendientes
    }


def obtener_resumen_anual(year):
    """Resumen del año en 2 consultas (antes eran 24: una por mes y métrica)."""
    year = int(year)
    fecha_inicio = f"{year}-01-01"
    fecha_fin = f"{year + 1}-01-01"

    with obtener_conexion() as conn:
        r = conn.execute(
            f"""SELECT COALESCE(SUM(precio_venta),0) as ingresos,
                       COALESCE(SUM(ganancia),0) as ganancia_pedidos,
                       COUNT(*) as num_pedidos
                FROM pedidos
                WHERE fecha >= ? AND fecha < ? AND {_COND_ACTIVO}""",
            (fecha_inicio, fecha_fin)
        ).fetchone()
        r2 = conn.execute(
            "SELECT COALESCE(SUM(monto),0) as gastos FROM gastos WHERE fecha >= ? AND fecha < ?",
            (fecha_inicio, fecha_fin)
        ).fetchone()

    ingresos = r["ingresos"]
    gastos = r2["gastos"]
    ganancia = ingresos - gastos
    return {
        "ingresos": ingresos,
        "gastos": gastos,
        "ganancia_neta": ganancia,
        "margen": (ganancia / ingresos * 100) if ingresos > 0 else 0,
        "num_pedidos": r["num_pedidos"],
    }


def obtener_ganancia_ultimos_dias(dias=30):
    """Retorna ganancia por día de los últimos N días para el gráfico."""
    with obtener_conexion() as conn:
        rows = conn.execute(f"""
            SELECT fecha, COALESCE(SUM(ganancia), 0) as ganancia
            FROM pedidos
            WHERE fecha >= date('now', ?) AND {_COND_ACTIVO}
            GROUP BY fecha
            ORDER BY fecha ASC
        """, (f"-{dias} days",)).fetchall()
    return [dict(r) for r in rows]


def obtener_gastos_por_categoria(fecha_desde=None, fecha_hasta=None):
    """Retorna suma de gastos agrupada por categoría.

    Con filtro de fechas se mantienen TODAS las categorías (las que no tienen
    gastos en el rango devuelven 0) para que el gráfico de pastel no haga
    desaparecer categorías sin movimiento.
    """
    query = """
        SELECT c.nombre,
               COALESCE(SUM(CASE WHEN g.id IS NOT NULL THEN g.monto ELSE 0 END), 0) as total
        FROM categorias_gastos c
        LEFT JOIN gastos g ON g.categoria_id = c.id
    """
    params = []
    if fecha_desde and fecha_hasta:
        query += " AND g.fecha BETWEEN ? AND ?"
        params = [fecha_desde, fecha_hasta]
    query += " GROUP BY c.id ORDER BY total DESC"

    with obtener_conexion() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def obtener_ingresos_por_mes(year):
    """Retorna ingresos agrupados por mes para un año dado."""
    year = int(year)
    with obtener_conexion() as conn:
        rows = conn.execute(f"""
            SELECT strftime('%m', fecha) as mes, COALESCE(SUM(precio_venta), 0) as total
            FROM pedidos
            WHERE fecha >= ? AND fecha < ? AND {_COND_ACTIVO}
            GROUP BY mes
            ORDER BY mes
        """, (f"{year}-01-01", f"{year + 1}-01-01")).fetchall()
    return [dict(r) for r in rows]


def obtener_pedidos_proximos(dias_antelacion=2):
    """Retorna pedidos cuya fecha de entrega es en los próximos N días."""
    with obtener_conexion() as conn:
        rows = conn.execute("""
            SELECT p.*, c.nombre AS cliente_nombre
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            WHERE p.estado = 'pendiente'
              AND p.fecha_entrega BETWEEN date('now') AND date('now', ?)
            ORDER BY p.fecha_entrega ASC
        """, (f"+{dias_antelacion} days",)).fetchall()
    return [dict(r) for r in rows]


def obtener_estadisticas_cliente(cliente_id):
    """Retorna estadísticas de pedidos de un cliente específico."""
    with obtener_conexion() as conn:
        r = conn.execute(f"""
            SELECT COUNT(*) as total_pedidos,
                   COALESCE(SUM(precio_venta), 0) as total_gastado,
                   COALESCE(SUM(ganancia), 0) as ganancia_total,
                   MAX(fecha) as ultimo_pedido
            FROM pedidos WHERE cliente_id=? AND {_COND_ACTIVO}
        """, (cliente_id,)).fetchone()
    return dict(r)


def obtener_clientes_inactivos(dias=90):
    """Retorna clientes cuyo último pedido fue hace más de X días."""
    with obtener_conexion() as conn:
        rows = conn.execute(f"""
            SELECT c.*, MAX(p.fecha) as ultimo_pedido
            FROM clientes c
            JOIN pedidos p ON c.id = p.cliente_id
            WHERE {_COND_ACTIVO}
            GROUP BY c.id
            HAVING ultimo_pedido <= date('now', ?)
            ORDER BY ultimo_pedido ASC
        """, (f"-{dias} days",)).fetchall()
    return [dict(r) for r in rows]


# ======================== CATÁLOGO DE PRODUCTOS ========================

def agregar_producto_catalogo(nombre, descripcion, filamento_base_id, gramos, horas, precio):
    """Agrega un nuevo producto al catálogo."""
    with obtener_conexion() as conn:
        conn.execute(
            """INSERT INTO catalogo (nombre, descripcion, filamento_base_id, gramos_estimados,
               horas_estimadas, precio_sugerido) VALUES (?,?,?,?,?,?)""",
            (nombre, descripcion, filamento_base_id, gramos, horas, precio)
        )


def obtener_catalogo():
    """Retorna todos los productos del catálogo."""
    with obtener_conexion() as conn:
        rows = conn.execute("""
            SELECT c.*, f.nombre as filamento_nombre, f.material as filamento_material
            FROM catalogo c
            LEFT JOIN filamentos f ON c.filamento_base_id = f.id
            ORDER BY c.nombre
        """).fetchall()
    return [dict(r) for r in rows]


def actualizar_producto_catalogo(id, nombre, descripcion, filamento_base_id, gramos, horas, precio):
    """Actualiza un producto del catálogo."""
    with obtener_conexion() as conn:
        conn.execute(
            """UPDATE catalogo SET nombre=?, descripcion=?, filamento_base_id=?,
               gramos_estimados=?, horas_estimadas=?, precio_sugerido=? WHERE id=?""",
            (nombre, descripcion, filamento_base_id, gramos, horas, precio, id)
        )


def eliminar_producto_catalogo(id):
    """Elimina un producto del catálogo."""
    with obtener_conexion() as conn:
        conn.execute("DELETE FROM catalogo WHERE id=?", (id,))
