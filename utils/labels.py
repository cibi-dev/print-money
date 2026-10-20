# utils/labels.py – Utilidades para construir desplegables sin colisiones


def mapa_por_etiqueta(items, formatear):
    """Construye {etiqueta: item} garantizando que las etiquetas sean únicas.

    Los clientes se indexaban por nombre y los filamentos por "nombre
    (material)". Como `clientes.nombre` no tiene restricción UNIQUE, dos
    clientes homónimos colapsaban en una sola entrada del dict: uno quedaba
    inaccesible y los pedidos se asignaban al equivocado.

    Si una etiqueta se repite se le añade un discriminador "(2)", "(3)"...
    de modo que todas las entradas siguen siendo seleccionables.

    Args:
        items: iterable de elementos
        formatear: función que convierte un elemento en su etiqueta
    Returns:
        dict etiqueta -> elemento
    """
    conteo = {}
    mapa = {}
    for item in items:
        base = formatear(item)
        conteo[base] = conteo.get(base, 0) + 1
        etiqueta = base if conteo[base] == 1 else f"{base} ({conteo[base]})"
        mapa[etiqueta] = item
    return mapa
