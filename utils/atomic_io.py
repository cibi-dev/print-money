import json
import os


def escribir_json_atomico(ruta: str, datos) -> None:
    """Escribe JSON de forma atómica: tmp + fsync + os.replace."""
    texto = json.dumps(datos, indent=4, ensure_ascii=False)
    tmp = ruta + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, ruta)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
