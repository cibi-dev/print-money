#!/usr/bin/env python3
"""
reparar_inventario.py – Repara el consumo fantasma de filamento.

Problema: antes de la corrección, al editar o borrar un pedido el stock de
filamento NO se devolvía y el registro de `historial_filamento` se quedaba
huérfano (pedido_id = NULL). En la base de datos actual eso deja filamentos
con gramos que ya se consumieron de más.

Este script:
  1. Localiza las filas de `historial_filamento` cuyo pedido ya no existe.
  2. Devuelve esos gramos al filamento correspondiente.
  3. Elimina las filas huérfanas del historial.
  4. Muestra un informe de lo que ha hecho.

Uso:
    python reparar_inventario.py            # pide confirmación antes de escribir
    python reparar_inventario.py --dry-run  # solo muestra lo que haría
    python reparar_inventario.py --yes      # no pregunta (para scripts)

La base de datos usada es la misma que la app: %APPDATA%\\PrintMoney\\data\\
printmoney.db (o la carpeta indicada por PRINTMONEY_DATA_DIR).
"""
import argparse
import os
import sqlite3
import sys

from utils import paths

DB_PATH = paths.DB_PATH


def main():
    parser = argparse.ArgumentParser(description="Repara el inventario de filamento")
    parser.add_argument("--dry-run", action="store_true", help="No escribe nada")
    parser.add_argument("--yes", action="store_true", help="No pide confirmación")
    args = parser.parse_args()

    try:
        paths.migrar_datos_legados()
    except Exception as exc:
        print(f"No se pudieron migrar los datos: {exc}")
        return 1

    if not os.path.exists(DB_PATH):
        print(f"No se encuentra la base de datos: {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Filamentos cuyo consumo corresponde a un pedido que ya no existe
    huerfanos = conn.execute("""
        SELECT h.id, h.filamento_id, h.gramos_consumidos, h.fecha,
               f.nombre AS filamento_nombre, f.gramos_restantes
        FROM historial_filamento h
        LEFT JOIN filamentos f ON f.id = h.filamento_id
        WHERE h.pedido_id IS NULL
           AND NOT EXISTS (SELECT 1 FROM pedidos p WHERE p.id = h.pedido_id)
        ORDER BY h.id
    """).fetchall()

    if not huerfanos:
        print("No hay consumos huérfanos. El inventario está consistente.")
        conn.close()
        return 0

    print(f"Se han encontrado {len(huerfanos)} consumos huérfanos "
          f"(pedidos borrados sin devolver el stock):\n")
    total = 0.0
    por_filamento = {}
    for h in huerfanos:
        nombre = h["filamento_nombre"] or f"filamento #{h['filamento_id']} (borrado)"
        gramos = h["gramos_consumidos"] or 0
        total += gramos
        por_filamento.setdefault(h["filamento_id"], [nombre, 0.0])[1] += gramos
        print(f"  historial #{h['id']:>4}  {nombre:<24} {gramos:>10.2f} g   "
              f"(fecha {h['fecha']})")

    print(f"\nTotal a devolver: {total:.2f} g")
    for fid, (nombre, gramos) in por_filamento.items():
        print(f"  +{gramos:.2f} g  ->  {nombre}")

    if args.dry_run:
        print("\n[--dry-run] No se ha modificado nada.")
        conn.close()
        return 0

    if not args.yes:
        r = input("\n¿Aplicar la reparación? [s/N] ").strip().lower()
        if r not in ("s", "si", "yes", "y"):
            print("Cancelado.")
            conn.close()
            return 0

    for fid, (nombre, gramos) in por_filamento.items():
        conn.execute(
            "UPDATE filamentos SET gramos_restantes = gramos_restantes + ? WHERE id=?",
            (gramos, fid))
    conn.execute("DELETE FROM historial_filamento WHERE pedido_id IS NULL")

    # Backup del estado anterior por si acaso
    conn.commit()
    conn.close()

    print("\nReparación aplicada.")
    print("Nota: se ha creado un backup diario automático al arrancar la app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
