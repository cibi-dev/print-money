# db_manager.py – Gestor de base de datos SQLite para PrintMoney
# Maneja la creación del esquema, conexión y operaciones CRUD principales

import sqlite3
import os
import shutil
from datetime import date, datetime

import sys

# Ruta de la base de datos
if getattr(sys, 'frozen', False):
    # Si es un ejecutable PyInstaller, usar la carpeta donde está el .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)

DB_PATH = os.path.join(BASE_DIR, "data", "printmoney.db")
BACKUP_DIR = os.path.join(BASE_DIR, "data", "backups")

def obtener_conexion():
    """Retorna una conexión a la base de datos SQLite con row_factory para dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_db():
    """Crea todas las tablas si no existen. Se llama en el arranque de la app."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)

    conn = obtener_conexion()
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

    conn.commit()
    conn.close()


def hacer_backup_diario():
    """Crea un backup de la base de datos con fecha actual si no existe ya."""
    if not os.path.exists(DB_PATH):
        return
    nombre_backup = f"backup_{date.today().strftime('%Y-%m-%d')}.db"
    ruta_backup = os.path.join(BACKUP_DIR, nombre_backup)
    if not os.path.exists(ruta_backup):
        shutil.copy2(DB_PATH, ruta_backup)
        return True  # Backup realizado
    return False  # Ya existía


# ======================== CLIENTES ========================

def agregar_cliente(nombre, email="", telefono="", direccion="", notas=""):
    """Inserta un nuevo cliente en la base de datos."""
    conn = obtener_conexion()
    conn.execute(
        "INSERT INTO clientes (nombre, email, telefono, direccion, notas) VALUES (?,?,?,?,?)",
        (nombre, email, telefono, direccion, notas)
    )
    conn.commit()
    conn.close()


def obtener_clientes():
    """Retorna lista de todos los clientes."""
    conn = obtener_conexion()
    rows = conn.execute("SELECT * FROM clientes ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def actualizar_cliente(id, nombre, email, telefono, direccion, notas):
    """Actualiza los datos de un cliente existente."""
    conn = obtener_conexion()
    conn.execute(
        "UPDATE clientes SET nombre=?, email=?, telefono=?, direccion=?, notas=? WHERE id=?",
        (nombre, email, telefono, direccion, notas, id)
    )
    conn.commit()
    conn.close()


def eliminar_cliente(id):
    """Elimina un cliente por ID."""
    conn = obtener_conexion()
    conn.execute("DELETE FROM clientes WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ======================== FILAMENTOS ========================

def agregar_filamento(nombre, material, color, gramos, precio_kg, umbral, proveedor="", notas=""):
    """Agrega un nuevo filamento al inventario."""
    conn = obtener_conexion()
    conn.execute(
        """INSERT INTO filamentos (nombre, material, color, gramos_restantes, precio_por_kg, umbral_bajo, proveedor, notas)
           VALUES (?,?,?,?,?,?,?,?)""",
        (nombre, material, color, gramos, precio_kg, umbral, proveedor, notas)
    )
    conn.commit()
    conn.close()


def obtener_filamentos():
    """Retorna todos los filamentos del inventario."""
    conn = obtener_conexion()
    rows = conn.execute("SELECT * FROM filamentos ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def actualizar_gramos_filamento(filamento_id, gramos_a_restar):
    """Descuenta gramos del inventario de un filamento específico."""
    conn = obtener_conexion()
    conn.execute(
        "UPDATE filamentos SET gramos_restantes = MAX(0, gramos_restantes - ?) WHERE id=?",
        (gramos_a_restar, filamento_id)
    )
    conn.commit()
    conn.close()


def actualizar_filamento(id, nombre, material, color, gramos, precio_kg, umbral, proveedor, notas):
    """Actualiza los datos de un filamento."""
    conn = obtener_conexion()
    conn.execute(
        """UPDATE filamentos SET nombre=?, material=?, color=?, gramos_restantes=?,
           precio_por_kg=?, umbral_bajo=?, proveedor=?, notas=? WHERE id=?""",
        (nombre, material, color, gramos, precio_kg, umbral, proveedor, notas, id)
    )
    conn.commit()
    conn.close()


def eliminar_filamento(id):
    """Elimina un filamento del inventario."""
    conn = obtener_conexion()
    conn.execute("DELETE FROM filamentos WHERE id=?", (id,))
    conn.commit()
    conn.close()


def obtener_filamentos_bajo_umbral():
    """Retorna filamentos cuyo stock está por debajo del umbral configurado."""
    conn = obtener_conexion()
    rows = conn.execute(
        "SELECT * FROM filamentos WHERE gramos_restantes < umbral_bajo"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ======================== PEDIDOS ========================

def agregar_pedido(datos: dict):
    """
    Inserta un nuevo pedido y descuenta gramos del inventario automáticamente.
    datos: dict con todos los campos del pedido.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()

    # Calcular ganancia y margen
    costo_total = datos.get("costo_material", 0) + datos.get("costo_tiempo", 0) + datos.get("costo_envio", 0)
    precio_venta = datos.get("precio_venta", 0)
    ganancia = precio_venta - costo_total
    margen = (ganancia / precio_venta * 100) if precio_venta > 0 else 0

    cursor.execute("""
        INSERT INTO pedidos (fecha, cliente_id, descripcion, filamento_id, gramos_usados,
            horas_impresion, costo_material, costo_tiempo, costo_envio, precio_venta,
            ganancia, margen_porcentaje, fecha_entrega, estado, notas)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        datos.get("fecha", str(date.today())),
        datos.get("cliente_id"),
        datos.get("descripcion", ""),
        datos.get("filamento_id"),
        datos.get("gramos_usados", 0),
        datos.get("horas_impresion", 0),
        datos.get("costo_material", 0),
        datos.get("costo_tiempo", 0),
        datos.get("costo_envio", 0),
        precio_venta,
        ganancia,
        margen,
        datos.get("fecha_entrega", ""),
        datos.get("estado", "pendiente"),
        datos.get("notas", "")
    ))
    pedido_id = cursor.lastrowid

    # Descontar gramos del inventario si hay filamento asignado
    filamento_id = datos.get("filamento_id")
    gramos_usados = datos.get("gramos_usados", 0)
    if filamento_id and gramos_usados > 0:
        conn.execute(
            "UPDATE filamentos SET gramos_restantes = MAX(0, gramos_restantes - ?) WHERE id=?",
            (gramos_usados, filamento_id)
        )
        # Registrar en historial
        conn.execute(
            "INSERT INTO historial_filamento (filamento_id, pedido_id, gramos_consumidos) VALUES (?,?,?)",
            (filamento_id, pedido_id, gramos_usados)
        )

    conn.commit()
    conn.close()
    return pedido_id


def obtener_pedidos(filtro_cliente_id=None, filtro_estado=None, filtro_fecha_desde=None, filtro_fecha_hasta=None):
    """Retorna pedidos con joins a clientes y filamentos, con filtros opcionales."""
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
    query += " ORDER BY p.fecha DESC"

    conn = obtener_conexion()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def actualizar_pedido(id, datos: dict):
    """Actualiza un pedido existente."""
    costo_total = datos.get("costo_material", 0) + datos.get("costo_tiempo", 0) + datos.get("costo_envio", 0)
    precio_venta = datos.get("precio_venta", 0)
    ganancia = precio_venta - costo_total
    margen = (ganancia / precio_venta * 100) if precio_venta > 0 else 0

    conn = obtener_conexion()
    conn.execute("""
        UPDATE pedidos SET fecha=?, cliente_id=?, descripcion=?, filamento_id=?, gramos_usados=?,
            horas_impresion=?, costo_material=?, costo_tiempo=?, costo_envio=?, precio_venta=?,
            ganancia=?, margen_porcentaje=?, fecha_entrega=?, estado=?, notas=?
        WHERE id=?
    """, (
        datos.get("fecha"), datos.get("cliente_id"), datos.get("descripcion"),
        datos.get("filamento_id"), datos.get("gramos_usados"), datos.get("horas_impresion"),
        datos.get("costo_material"), datos.get("costo_tiempo"), datos.get("costo_envio"),
        precio_venta, ganancia, margen, datos.get("fecha_entrega"),
        datos.get("estado"), datos.get("notas"), id
    ))
    conn.commit()
    conn.close()


def eliminar_pedido(id):
    """Elimina un pedido por ID."""
    conn = obtener_conexion()
    conn.execute("DELETE FROM pedidos WHERE id=?", (id,))
    conn.commit()
    conn.close()


def marcar_factura_generada(pedido_id):
    """Marca un pedido como factura generada."""
    conn = obtener_conexion()
    conn.execute("UPDATE pedidos SET factura_generada=1 WHERE id=?", (pedido_id,))
    conn.commit()
    conn.close()


# ======================== GASTOS ========================

def obtener_categorias_gastos():
    """Retorna todas las categorías de gastos."""
    conn = obtener_conexion()
    rows = conn.execute("SELECT * FROM categorias_gastos ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def agregar_categoria_gasto(nombre):
    """Agrega una nueva categoría de gasto."""
    conn = obtener_conexion()
    conn.execute("INSERT OR IGNORE INTO categorias_gastos (nombre) VALUES (?)", (nombre,))
    conn.commit()
    conn.close()


def agregar_gasto(fecha, categoria_id, descripcion, monto, recurrente=0, frecuencia="mensual", notas=""):
    """Inserta un nuevo gasto."""
    conn = obtener_conexion()
    conn.execute(
        "INSERT INTO gastos (fecha, categoria_id, descripcion, monto, recurrente, frecuencia, notas) VALUES (?,?,?,?,?,?,?)",
        (fecha, categoria_id, descripcion, monto, recurrente, frecuencia, notas)
    )
    conn.commit()
    conn.close()


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
    query += " ORDER BY g.fecha DESC"

    conn = obtener_conexion()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def eliminar_gasto(id):
    """Elimina un gasto por ID."""
    conn = obtener_conexion()
    conn.execute("DELETE FROM gastos WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ======================== REPORTES / ESTADÍSTICAS ========================

def obtener_estadisticas_mes(year, month):
    """Retorna ingresos, gastos y ganancia neta de un mes específico."""
    conn = obtener_conexion()

    fecha_inicio = f"{year}-{month:02d}-01"
    # Último día del mes
    if month == 12:
        fecha_fin = f"{year+1}-01-01"
    else:
        fecha_fin = f"{year}-{month+1:02d}-01"

    # Ingresos del mes (suma de ventas)
    r = conn.execute(
        "SELECT COALESCE(SUM(precio_venta),0) as total FROM pedidos WHERE fecha >= ? AND fecha < ?",
        (fecha_inicio, fecha_fin)
    ).fetchone()
    ingresos = r["total"]

    # Gastos del mes
    r = conn.execute(
        "SELECT COALESCE(SUM(monto),0) as total FROM gastos WHERE fecha >= ? AND fecha < ?",
        (fecha_inicio, fecha_fin)
    ).fetchone()
    gastos = r["total"]

    # Pedidos totales del mes
    r = conn.execute(
        "SELECT COUNT(*) as total FROM pedidos WHERE fecha >= ? AND fecha < ?",
        (fecha_inicio, fecha_fin)
    ).fetchone()
    num_pedidos = r["total"]

    # Ganancia neta de pedidos
    r = conn.execute(
        "SELECT COALESCE(SUM(ganancia),0) as total FROM pedidos WHERE fecha >= ? AND fecha < ?",
        (fecha_inicio, fecha_fin)
    ).fetchone()
    ganancia_pedidos = r["total"]

    # Pedidos pendientes (sin importar mes)
    r = conn.execute(
        "SELECT COUNT(*) as total FROM pedidos WHERE estado='pendiente'"
    ).fetchone()
    pendientes = r["total"]

    conn.close()
    return {
        "ingresos": ingresos,
        "gastos": gastos,
        "ganancia_neta": ganancia_pedidos - gastos,
        "margen": (ganancia_pedidos / ingresos * 100) if ingresos > 0 else 0,
        "num_pedidos": num_pedidos,
        "pendientes": pendientes
    }


def obtener_ganancia_ultimos_dias(dias=30):
    """Retorna ganancia por día de los últimos N días para el gráfico."""
    conn = obtener_conexion()
    rows = conn.execute("""
        SELECT fecha, COALESCE(SUM(ganancia), 0) as ganancia
        FROM pedidos
        WHERE fecha >= date('now', ?)
        GROUP BY fecha
        ORDER BY fecha ASC
    """, (f"-{dias} days",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_gastos_por_categoria(fecha_desde=None, fecha_hasta=None):
    """Retorna suma de gastos agrupada por categoría."""
    query = """
        SELECT c.nombre, COALESCE(SUM(g.monto), 0) as total
        FROM categorias_gastos c
        LEFT JOIN gastos g ON g.categoria_id = c.id
    """
    params = []
    if fecha_desde and fecha_hasta:
        query += " WHERE g.fecha BETWEEN ? AND ?"
        params = [fecha_desde, fecha_hasta]
    query += " GROUP BY c.id ORDER BY total DESC"

    conn = obtener_conexion()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_ingresos_por_mes(year):
    """Retorna ingresos agrupados por mes para un año dado."""
    conn = obtener_conexion()
    rows = conn.execute("""
        SELECT strftime('%m', fecha) as mes, COALESCE(SUM(precio_venta), 0) as total
        FROM pedidos
        WHERE strftime('%Y', fecha) = ?
        GROUP BY mes
        ORDER BY mes
    """, (str(year),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_pedidos_proximos(dias_antelacion=2):
    """Retorna pedidos cuya fecha de entrega es en los próximos N días."""
    conn = obtener_conexion()
    rows = conn.execute("""
        SELECT p.*, c.nombre AS cliente_nombre
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.estado = 'pendiente'
          AND p.fecha_entrega BETWEEN date('now') AND date('now', ?)
        ORDER BY p.fecha_entrega ASC
    """, (f"+{dias_antelacion} days",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_estadisticas_cliente(cliente_id):
    """Retorna estadísticas de pedidos de un cliente específico."""
    conn = obtener_conexion()
    r = conn.execute("""
        SELECT COUNT(*) as total_pedidos,
               COALESCE(SUM(precio_venta), 0) as total_gastado,
               COALESCE(SUM(ganancia), 0) as ganancia_total,
               MAX(fecha) as ultimo_pedido
        FROM pedidos WHERE cliente_id=?
    """, (cliente_id,)).fetchone()
    conn.close()
    return dict(r)

def obtener_clientes_inactivos(dias=90):
    """Retorna clientes cuyo último pedido fue hace más de X días."""
    conn = obtener_conexion()
    rows = conn.execute("""
        SELECT c.*, MAX(p.fecha) as ultimo_pedido
        FROM clientes c
        JOIN pedidos p ON c.id = p.cliente_id
        GROUP BY c.id
        HAVING ultimo_pedido <= date('now', ?)
        ORDER BY ultimo_pedido ASC
    """, (f"-{dias} days",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ======================== CATÁLOGO DE PRODUCTOS ========================

def agregar_producto_catalogo(nombre, descripcion, filamento_base_id, gramos, horas, precio):
    """Agrega un nuevo producto al catálogo."""
    conn = obtener_conexion()
    conn.execute(
        """INSERT INTO catalogo (nombre, descripcion, filamento_base_id, gramos_estimados, 
           horas_estimadas, precio_sugerido) VALUES (?,?,?,?,?,?)""",
        (nombre, descripcion, filamento_base_id, gramos, horas, precio)
    )
    conn.commit()
    conn.close()

def obtener_catalogo():
    """Retorna todos los productos del catálogo."""
    conn = obtener_conexion()
    rows = conn.execute("""
        SELECT c.*, f.nombre as filamento_nombre, f.material as filamento_material
        FROM catalogo c
        LEFT JOIN filamentos f ON c.filamento_base_id = f.id
        ORDER BY c.nombre
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def actualizar_producto_catalogo(id, nombre, descripcion, filamento_base_id, gramos, horas, precio):
    """Actualiza un producto del catálogo."""
    conn = obtener_conexion()
    conn.execute(
        """UPDATE catalogo SET nombre=?, descripcion=?, filamento_base_id=?, 
           gramos_estimados=?, horas_estimadas=?, precio_sugerido=? WHERE id=?""",
        (nombre, descripcion, filamento_base_id, gramos, horas, precio, id)
    )
    conn.commit()
    conn.close()

def eliminar_producto_catalogo(id):
    """Elimina un producto del catálogo."""
    conn = obtener_conexion()
    conn.execute("DELETE FROM catalogo WHERE id=?", (id,))
    conn.commit()
    conn.close()

