"""Rutas de datos y recursos de PrintMoney.

Los datos escribibles viven en %APPDATA%\\PrintMoney (o en
$XDG_DATA_HOME/PrintMoney) para que la app funcione instalada en una carpeta
de solo lectura. Los assets siguen junto al ejecutable o en _MEIPASS.
"""
import os
import shutil
import sqlite3
import sys

APP_NAME = "PrintMoney"


def _app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resource_dir() -> str:
    return getattr(sys, "_MEIPASS", _app_dir())


APP_DIR = _app_dir()
RESOURCE_DIR = _resource_dir()
ASSETS_DIR = os.path.join(RESOURCE_DIR, "assets")


def _candidatos_data_dir():
    override = os.environ.get("PRINTMONEY_DATA_DIR")
    if override:
        yield os.path.abspath(override)
        return
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        yield os.path.join(base, APP_NAME)
        local = os.environ.get("LOCALAPPDATA")
        if local:
            yield os.path.join(local, APP_NAME)
        yield os.path.join(APP_DIR, f"{APP_NAME}Data")
    else:
        yield os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)
        yield os.path.join(APP_DIR, f"{APP_NAME}Data")


def _puede_escribir(ruta: str) -> bool:
    try:
        os.makedirs(os.path.join(ruta, "data", "backups"), exist_ok=True)
        prueba = os.path.join(ruta, ".write_test")
        with open(prueba, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(prueba)
        return True
    except OSError:
        return False


def _data_dir() -> str:
    candidatos = list(_candidatos_data_dir())
    for candidato in candidatos:
        if _puede_escribir(candidato):
            return os.path.abspath(candidato)
    return os.path.abspath(candidatos[0])


DATA_DIR = _data_dir()
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
LOG_PATH = os.path.join(DATA_DIR, "printmoney.log")
DB_DIR = os.path.join(DATA_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "printmoney.db")
BACKUP_DIR = os.path.join(DB_DIR, "backups")


def legacy_dir() -> str:
    override = os.environ.get("PRINTMONEY_LEGACY_DIR")
    return os.path.abspath(override) if override else APP_DIR


def _rutas_legadas():
    base = legacy_dir()
    return (
        os.path.join(base, "config.json"),
        os.path.join(base, "data", "printmoney.db"),
        os.path.join(base, "data", "backups"),
    )


def resolver_recurso(ruta: str) -> str:
    """Resuelve una ruta relativa de asset contra el directorio de recursos."""
    if not ruta:
        return ""
    if os.path.isabs(ruta):
        return ruta
    normal = ruta.replace("\\", "/")
    if normal.startswith("assets/"):
        return os.path.join(RESOURCE_DIR, normal)
    return os.path.join(APP_DIR, ruta)


def asegurar_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _copiar_db(origen: str, destino: str) -> None:
    fuente = sqlite3.connect(origen)
    try:
        salida = sqlite3.connect(destino)
        try:
            fuente.backup(salida)
        finally:
            salida.close()
    finally:
        fuente.close()


_migrado = None


def migrar_datos_legados():
    """Copia config, base de datos y backups de la ubicación antigua.

    No borra ni modifica los archivos originales. Es idempotente: solo copia
    lo que aún no existe en el destino.
    """
    global _migrado
    if _migrado is not None:
        return _migrado

    resultado = {"config": False, "db": False, "backups": 0}
    if os.environ.get("PRINTMONEY_DISABLE_MIGRATION") == "1":
        _migrado = resultado
        return resultado
    if os.path.abspath(DATA_DIR) == os.path.abspath(legacy_dir()):
        _migrado = resultado
        return resultado

    asegurar_dirs()
    config_origen, db_origen, backups_origen = _rutas_legadas()

    if os.path.isfile(config_origen) and not os.path.exists(CONFIG_PATH):
        shutil.copy2(config_origen, CONFIG_PATH)
        resultado["config"] = True

    if os.path.isfile(db_origen) and not os.path.exists(DB_PATH):
        _copiar_db(db_origen, DB_PATH)
        resultado["db"] = True

    if os.path.isdir(backups_origen):
        for nombre in os.listdir(backups_origen):
            origen = os.path.join(backups_origen, nombre)
            destino = os.path.join(BACKUP_DIR, nombre)
            if os.path.isfile(origen) and not os.path.exists(destino):
                shutil.copy2(origen, destino)
                resultado["backups"] += 1

    _migrado = resultado
    return resultado
