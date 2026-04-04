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
        notifier.show_toast(
            titulo,
            mensaje,
            duration=duracion,
            threaded=True
        )
        return
    except ImportError:
        pass
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
    except ImportError:
        pass
    except Exception:
        pass
