# ui/clients.py – Vista de Clientes
# Lista de clientes con historial de pedidos y estadísticas por cliente

import customtkinter as ctk
from tkinter import messagebox
import db_manager
from datetime import datetime, date
from utils.i18n import T
from ui import theme as th
from ui import components as ui


class ClientsView(ctk.CTkFrame):
    """Vista de gestión de clientes con historial y estadísticas."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=th.BG, corner_radius=0, **kwargs)
        self.app = app
        self._cliente_seleccionado = None
        self._todos_clientes = []
        self._debounce_buscar = None
        self._construir_ui()

    def on_show(self):
        self._cargar_clientes()

    def _construir_ui(self):
        _, zona_acciones = ui.page_header(self, T("clients_title"))
        ui.primary_button(zona_acciones, T("clients_new"),
                          self._nuevo_cliente, width=150).pack(side="right")

        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=th.PAD_PAGE, pady=14)
        frame_main.columnconfigure(0, weight=2)
        frame_main.columnconfigure(1, weight=2)
        frame_main.columnconfigure(2, weight=3)
        frame_main.rowconfigure(0, weight=1)

        frame_lista = ui.card(frame_main)
        frame_lista.grid(row=0, column=0, padx=(0, th.GAP), sticky="nsew")

        ui.section_title(frame_lista, T("clients_list")).pack(
            anchor="w", padx=14, pady=(14, 6))

        self.entry_buscar = ui.entry(frame_lista, T("clients_search_ph"), height=32)
        self.entry_buscar.pack(fill="x", padx=10, pady=(0, 6))
        self.entry_buscar.bind("<KeyRelease>", self._on_buscar_tecla)

        self.frame_lista_scroll = ui.scrollable(frame_lista)
        self.frame_lista_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 6))

        self.frame_form = ui.scrollable(frame_main, fg_color=th.CARD,
                                        corner_radius=th.RADIUS_CARD,
                                        border_width=1, border_color=th.BORDER)
        self.frame_form.grid(row=0, column=1, padx=(0, th.GAP), sticky="nsew")
        self._construir_formulario(self.frame_form)

        frame_hist = ui.card(frame_main)
        frame_hist.grid(row=0, column=2, sticky="nsew")

        ui.section_title(frame_hist, T("clients_history")).pack(
            anchor="w", padx=14, pady=(14, 4))

        self.frame_stats = ctk.CTkFrame(frame_hist, fg_color=th.SURFACE,
                                        corner_radius=th.RADIUS_CTRL)
        self.frame_stats.pack(fill="x", padx=10, pady=(0, 8))
        self.lbl_stats = ctk.CTkLabel(self.frame_stats,
                                      text=T("clients_stats_empty"),
                                      text_color=th.SUB, font=th.fuente(th.FONT_LABEL),
                                      justify="left")
        self.lbl_stats.pack(padx=12, pady=10, anchor="w")

        self.frame_crm = ctk.CTkFrame(frame_hist, fg_color=th.YELLOW,
                                      corner_radius=th.RADIUS_CTRL)
        self.lbl_crm = ctk.CTkLabel(self.frame_crm, text=T("clients_crm_alert"),
                                    font=th.fuente(th.FONT_BODY, True),
                                    text_color=th.INK)
        self.lbl_crm.pack(side="left", padx=10, pady=8)
        ui.secondary_button(self.frame_crm, T("clients_crm_copy"),
                            self._copiar_mensaje_crm, width=100, height=26,
                            fg_color=th.BG, hover_color=th.SURFACE,
                            text_color=th.TEXT, border_width=0,
                            font=th.fuente(11, True)).pack(side="right", padx=10, pady=6)

        self.frame_hist_scroll = ui.scrollable(frame_hist)
        self.frame_hist_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 8))

    def _construir_formulario(self, parent):
        ui.section_title(parent, T("clients_form_title")).pack(
            anchor="w", padx=14, pady=(14, 4))

        def lbl(t):
            ui.section_label(parent, t).pack(anchor="w", padx=14, pady=(8, 2))

        def ent(ph=""):
            e = ui.entry(parent, ph)
            e.pack(fill="x", padx=14)
            return e

        lbl(T("clients_name")); self.ent_nombre = ent(T("clients_name_ph"))
        lbl(T("clients_email")); self.ent_email = ent("cliente@email.com")
        lbl(T("clients_phone")); self.ent_telefono = ent("+1 555 000")
        lbl(T("clients_address")); self.ent_direccion = ent(T("clients_address_ph"))
        lbl(T("clients_notes")); self.ent_notas = ent(T("clients_notes_ph"))

        ui.divider(parent).pack(fill="x", padx=14, pady=12)

        ui.primary_button(parent, T("clients_save"), self._guardar_cliente,
                          height=th.H_BTN_LG).pack(fill="x", padx=14, pady=(0, 6))

        ui.danger_button(parent, T("clients_delete"), self._eliminar_cliente).pack(
            fill="x", padx=14, pady=(0, 14))

    def _cargar_clientes(self):
        for w in self.frame_lista_scroll.winfo_children():
            w.destroy()
        self._todos_clientes = db_manager.obtener_clientes()
        self._renderizar_clientes(self._todos_clientes)

    def _renderizar_clientes(self, clientes):
        for w in self.frame_lista_scroll.winfo_children():
            w.destroy()
        if not clientes:
            ui.empty_state(self.frame_lista_scroll, icono="👥",
                           titulo=T("clients_list"),
                           hint=T("clients_empty_hint"),
                           cta_texto=T("clients_new"),
                           cta_cmd=self._nuevo_cliente)
            return
        for c in clientes:
            btn = ctk.CTkButton(
                self.frame_lista_scroll,
                text=c["nombre"],
                fg_color="transparent", hover_color=th.HOVER,
                text_color=th.TEXT, anchor="w", height=36,
                font=th.fuente(th.FONT_BODY),
                command=lambda cid=c["id"]: self._seleccionar_cliente(cid)
            )
            btn.pack(fill="x", pady=1)

    def _on_buscar_tecla(self, event=None):
        if getattr(self, "_debounce_buscar", None) is not None:
            try:
                self.after_cancel(self._debounce_buscar)
            except Exception:
                pass
        self._debounce_buscar = self.after(250, self._filtrar_clientes)

    def _filtrar_clientes(self):
        texto = self.entry_buscar.get().lower()
        filtrados = [c for c in self._todos_clientes if texto in c["nombre"].lower()]
        self._renderizar_clientes(filtrados)

    def _seleccionar_cliente(self, cliente_id):
        self._cliente_seleccionado = cliente_id
        cliente = next((c for c in self._todos_clientes if c["id"] == cliente_id), None)
        if not cliente:
            return

        def set_e(e, val):
            e.delete(0, "end"); e.insert(0, str(val or ""))

        set_e(self.ent_nombre, cliente["nombre"])
        set_e(self.ent_email, cliente.get("email", ""))
        set_e(self.ent_telefono, cliente.get("telefono", ""))
        set_e(self.ent_direccion, cliente.get("direccion", ""))
        set_e(self.ent_notas, cliente.get("notas", ""))

        stats = db_manager.obtener_estadisticas_cliente(cliente_id)
        self.lbl_stats.configure(
            text=T("clients_stats_fmt",
                   orders=stats['total_pedidos'],
                   spent=stats['total_gastado'],
                   profit=stats['ganancia_total'])
        )

        inactivo = False
        if stats.get('ultimo_pedido'):
            try:
                ultimo = datetime.strptime(stats['ultimo_pedido'][:10], "%Y-%m-%d").date()
                if (date.today() - ultimo).days > 90:
                    inactivo = True
            except Exception:
                pass

        if inactivo:
            self.frame_crm.pack(fill="x", padx=10, pady=(0, th.GAP))
            self.frame_hist_scroll.pack_forget()
            self.frame_hist_scroll.pack(fill="both", expand=True, padx=4, pady=(0, th.GAP))
        else:
            self.frame_crm.pack_forget()

        for w in self.frame_hist_scroll.winfo_children():
            w.destroy()
        pedidos = db_manager.obtener_pedidos(filtro_cliente_id=cliente_id)
        for p in pedidos:
            fila = ctk.CTkFrame(self.frame_hist_scroll, fg_color=th.SURFACE,
                                corner_radius=th.RADIUS_CTRL)
            fila.pack(fill="x", pady=3, padx=2)
            fila.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(fila, text=(p.get('descripcion') or "—")[:38],
                         font=th.fuente(th.FONT_BODY, True), text_color=th.TEXT,
                         anchor="w").grid(row=0, column=0, sticky="ew",
                                          padx=(10, 6), pady=(8, 0))
            ctk.CTkLabel(fila, text=p.get('fecha', ''), font=th.fuente(10),
                         text_color=th.SUB_DIM, anchor="w").grid(
                             row=1, column=0, sticky="ew", padx=(10, 6), pady=(0, 8))
            ctk.CTkLabel(fila, text=f"${p.get('precio_venta', 0):.2f}",
                         font=th.fuente(th.FONT_BODY, True), text_color=th.ACCENT,
                         anchor="e").grid(row=0, column=1, rowspan=2, sticky="e",
                                          padx=(0, 10))

    def _nuevo_cliente(self):
        self._cliente_seleccionado = None
        for e in [self.ent_nombre, self.ent_email, self.ent_telefono,
                  self.ent_direccion, self.ent_notas]:
            e.delete(0, "end")

    def _guardar_cliente(self):
        nombre = self.ent_nombre.get().strip()
        if not nombre:
            messagebox.showwarning(T("warning"), T("clients_name_req"), parent=self.winfo_toplevel())
            return
        try:
            if self._cliente_seleccionado:
                db_manager.actualizar_cliente(
                    self._cliente_seleccionado, nombre,
                    self.ent_email.get(), self.ent_telefono.get(),
                    self.ent_direccion.get(), self.ent_notas.get()
                )
            else:
                db_manager.agregar_cliente(
                    nombre, self.ent_email.get(), self.ent_telefono.get(),
                    self.ent_direccion.get(), self.ent_notas.get()
                )
        except Exception as e:
            messagebox.showerror(T("error"), str(e), parent=self.winfo_toplevel())
            return
        self._nuevo_cliente()
        self._cargar_clientes()

    def _eliminar_cliente(self):
        if not self._cliente_seleccionado:
            messagebox.showwarning(T("warning"), T("clients_select"), parent=self.winfo_toplevel())
            return
        if messagebox.askyesno(T("confirm"), T("clients_confirm_del"), parent=self.winfo_toplevel()):
            try:
                db_manager.eliminar_cliente(self._cliente_seleccionado)
            except Exception as e:
                messagebox.showerror(T("error"), str(e), parent=self.winfo_toplevel())
                return
            self._nuevo_cliente()
            self._cargar_clientes()

    def _copiar_mensaje_crm(self):
        nombre_completo = self.ent_nombre.get().strip() or "amigo"
        nombre = nombre_completo.split()[0]
        texto = T("clients_crm_msg", name=nombre)
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.update()
        messagebox.showinfo(T("copied_msg"), T("clients_crm_copied"), parent=self.winfo_toplevel())
