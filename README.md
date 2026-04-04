# PrintMoney 🖨️💰

**Gestor de ganancias, gastos e ingresos netos para un negocio de impresión 3D.**

---

## Instalación

### 1. Requisitos
- Python 3.10 o superior
- Windows 10 / 11

### 2. Instalar dependencias

```bash
cd PrintMoney
pip install -r requirements.txt
```

### 3. Ejecutar la aplicación

```bash
python main.py
```

La base de datos `data/printmoney.db` se creará automáticamente en el primer arranque.

---

## Estructura del proyecto

```
PrintMoney/
├── main.py              # Punto de entrada – ventana principal y sidebar
├── db_manager.py        # Base de datos SQLite (esquema + CRUD)
├── requirements.txt     # Dependencias Python
├── config.json          # Configuración del negocio
├── assets/
│   └── icons/           # Iconos de la interfaz (generados automáticamente)
├── data/
│   ├── printmoney.db    # Base de datos (se crea al iniciar)
│   └── backups/         # Backups diarios automáticos
├── ui/
│   ├── dashboard.py     # Dashboard con KPIs y gráfico
│   ├── orders.py        # Gestión de pedidos
│   ├── expenses.py      # Gestión de gastos
│   ├── inventory.py     # Inventario de filamentos
│   ├── clients.py       # Gestión de clientes
│   ├── reports.py       # Reportes y gráficos
│   ├── calendar.py      # Calendario de entregas
│   ├── calculator.py    # Calculadora flotante de costo
│   └── settings.py      # Configuración general
└── utils/
    ├── pdf_invoice.py   # Generador de facturas PDF
    ├── export.py        # Exportar a Excel/PDF
    └── notifications.py # Notificaciones de Windows
```

---

## Características principales

| Módulo | Función |
|--------|---------|
| 📊 Dashboard | KPIs del mes, gráfico de ganancias, pedidos recientes |
| 📦 Pedidos | CRUD completo, descuento automático de inventario, facturas PDF |
| 💸 Gastos | Categorías editables, gastos recurrentes |
| 🧵 Inventario | Stock de filamentos con alertas de nivel bajo |
| 👥 Clientes | Historial de pedidos y estadísticas por cliente |
| 📈 Reportes | Gráficos de barras, línea y pastel + exportar Excel/PDF |
| 📅 Calendario | Vista mensual con fechas de entrega marcadas |
| ⚡ Calculadora | Cálculo de costo rápido flotante |
| ⚙️ Configuración | Datos del negocio, idioma (ES/EN), backup, notificaciones |

---

## Configuración inicial

1. Ve a **Configuración** en la barra lateral.
2. Completa los datos de tu negocio (nombre, dirección, logo).
3. Ajusta la **tarifa por hora** según tu costo.
4. Configura el **margen objetivo** para recibir alertas cuando una venta no alcance el margen.
5. Carga tu logo en formato `.png` para que aparezca en las facturas.

---

## Notas técnicas

- **Base de datos**: SQLite en `data/printmoney.db`
- **Backup automático**: diario en `data/backups/backup_YYYY-MM-DD.db`
- **Autoguardado**: cada 10 minutos (configurable)
- **Notificaciones**: usa `win10toast` con fallback a `plyer`

---

## Solución de problemas

**Error `No module named 'win10toast'`:**
```bash
pip install win10toast
```

**El calendario no aparece:**
```bash
pip install tkcalendar
```

**Error con iconos:**  
Los iconos se generan automáticamente como placeholders en la primera ejecución. Para usar iconos Feather reales, descarga los PNG de [feathericons.com](https://feathericons.com) y colócalos en `assets/icons/` con los nombres: `home.png`, `orders.png`, `expenses.png`, `inventory.png`, `clients.png`, `reports.png`, `calendar.png`, `calculator.png`, `settings.png`.
