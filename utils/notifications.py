# utils/notifications.py – Wrapper de notificaciones de escritorio para Windows
# Usa win10toast como primera opción, luego plyer como respaldo

def mostrar_notificacion(titulo: str, mensaje: str, duracion: int = 5):
    """
    Muestra una notificación toast de Windows.
    Intenta win10toast primero, luego plyer como fallback.
    No arroja excepciones si las librerías no están disponibles.
    """
    try:
        from win10toast import ToastNotifier
        notifier = ToastNotifier()
        # threaded=False: el toast se dibuja en el hilo del llamante (que es
        # daemon), así que no retrasa el cierre de la app. Además show_toast
        # devuelve False si ya había un toast activo: en ese caso hay que caer
        # a plyer en vez de descartar el aviso, porque la app dispara dos
        # notificaciones casi seguidas (backup al arrancar y pedidos próximos).
        if not notifier.show_toast(titulo, mensaje, duration=duracion, threaded=False):
            raise RuntimeError("ya hay una notificacion activa")
        return
    except Exception:
        pass

    # Fallback: plyer
    try:
        from plyer import notification
        notification.notify(
            title=titulo,
            message=mensaje,
            app_name="PrintMoney",
            timeout=duracion
        )
    except Exception:
        pass
