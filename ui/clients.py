# ui/clients.py – Vista de Clientes
# Lista de clientes con historial de pedidos y estadísticas por cliente

import customtkinter as ctk
from tkinter import messagebox
import db_manager
from datetime import datetime, date
from utils.i18n import T

COLOR_BG     = "#0F0F0F"
COLOR_CARD   = "#1E1E1E"
COLOR_ACCENT = "#00FF9D"
COLOR_TEXT   = "#FFFFFF"
COLOR_SUB    = "#888888"
COLOR_BORDER = "#2D2D2D"
COLOR_HOVER  = "#2A2A2A"
COLOR_RED    = "#FF4C4C"


class ClientsView(ctk.CTkFrame):
    """Vista de gestión de clientes con historial y estadísticas."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COLOR_BG, corner_radius=0, **kwargs)
        self.app = app
        self._cliente_seleccionado = None
        self._debounce_buscar = None
        self._construir_ui()

    def on_show(self):
        self._cargar_clientes()

    def _construir_ui(self):
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=28, pady=(22, 0))
        ctk.CTkLabel(frame_header, text=T("clients_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                     text_color=COLOR_TEXT).pack(side="left")
        ctk.CTkButton(frame_header, text=T("clients_new"),
                      fg_color=COLOR_ACCENT, hover_color="#00CC7A",
                      text_color="#000000", corner_radius=10,
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=self._nuevo_cliente, width=140, height=36).pack(side="right")

        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=28, pady=14)
        frame_main.columnconfigure(0, weight=2)
        frame_main.columnconfigure(1, weight=2)
        frame_main.columnconfigure(2, weight=3)
        frame_main.rowconfigure(0, weight=1)

        frame_lista = ctk.CTkFrame(frame_main, fg_color=COLOR_CARD, corner_radius=14,
                                   border_width=1, border_color=COLOR_BORDER)
        frame_lista.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        ctk.CTkLabel(frame_lista, text=T("clients_list"),
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=14, pady=(14, 6))

        self.entry_buscar = ctk.CTkEntry(frame_lista, placeholder_text=T("clients_search_ph"),
                                          fg_color="#252525", border_color=COLOR_BORDER,
                                          text_color=COLOR_TEXT, corner_radius=8, height=32)
        self.entry_buscar.pack(fill="x", padx=10, pady=(0, 6))
        self.entry_buscar.bind("<KeyRelease>", self._on_buscar_tecla)

        self.frame_lista_scroll = ctk.CTkScrollableFrame(frame_lista, fg_color="transparent")
        self.frame_lista_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 6))

        self.frame_form = ctk.CTkScrollableFrame(frame_main, fg_color=COLOR_CARD,
                                                  corner_radius=14, border_width=1,
                                                  border_color=COLOR_BORDER)
        self.frame_form.grid(row=0, column=1, padx=(0, 6), sticky="nsew")
        self._construir_formulario(self.frame_form)

        frame_hist = ctk.CTkFrame(frame_main, fg_color=COLOR_CARD, corner_radius=14,
                                  border_width=1, border_color=COLOR_BORDER)
        frame_hist.grid(row=0, column=2, sticky="nsew")

        ctk.CTkLabel(frame_hist, text=T("clients_history"),
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=14, pady=(14, 4))

        self.frame_stats = ctk.CTkFrame(frame_hist, fg_color="#252525", corner_radius=10)
        self.frame_stats.pack(fill="x", padx=10, pady=(0, 8))
        self.lbl_stats = ctk.CTkLabel(self.frame_stats,
                                       text=T("clients_stats_empty"),
                                       text_color=COLOR_SUB, font=ctk.CTkFont(size=11),
                                       justify="left")
        self.lbl_stats.pack(padx=12, pady=10, anchor="w")
        
        self.frame_crm = ctk.CTkFrame(frame_hist, fg_color="#FF9D00", corner_radius=10)
        self.lbl_crm = ctk.CTkLabel(self.frame_crm, text=T("clients_crm_alert"),
                                    font=ctk.CTkFont(size=12, weight="bold"), text_color="#111111")
        self.lbl_crm.pack(side="left", padx=10, pady=8)
        ctk.CTkButton(self.frame_crm, text=T("clients_crm_copy"), fg_color="#111111", hover_color="#222222",
                      text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"), height=26, width=100,
                      command=self._copiar_mensaje_crm).pack(side="right", padx=10, pady=6)

        self.frame_hist_scroll = ctk.CTkScrollableFrame(frame_hist, fg_color="transparent")
        self.frame_hist_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 8))

    def _construir_formulario(self, parent):
        ctk.CTkLabel(parent, text=T("clients_form_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=14, pady=(14, 4))

        def lbl(t): ctk.CTkLabel(parent, text=t, text_color=COLOR_SUB,
                                  font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(8, 2))
        def ent(ph=""):
            e = ctk.CTkEntry(parent, placeholder_text=ph, fg_color="#252525",
                             border_color=COLOR_BORDER, text_color=COLOR_TEXT,
                             corner_radius=8, height=34)
            e.pack(fill="x", padx=14)
            return e

        lbl(T("clients_name")); self.ent_nombre = ent(T("clients_name_ph"))
        lbl(T("clients_email")); self.ent_email = ent("cliente@email.com")
        lbl(T("clients_phone")); self.ent_telefono = ent("+1 555 000")
        lbl(T("clients_address")); self.ent_direccion = ent(T("clients_address_ph"))
        lbl(T("clients_notes")); self.ent_notas = ent(T("clients_notes_ph"))

        ctk.CTkFrame(parent, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=14, pady=12)

        ctk.CTkButton(parent, text=T("clients_save"),
                      fg_color=COLOR_ACCENT, hover_color="#00CC7A",
                      text_color="#000000",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      height=40, corner_radius=10,
                      command=self._guardar_cliente).pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkButton(parent, text=T("clients_delete"),
                      fg_color="#2D0000", hover_color="#3D0000",
                      text_color=COLOR_RED, height=34, corner_radius=10,
                      command=self._eliminar_cliente).pack(fill="x", padx=14, pady=(0, 14))

    def _cargar_clientes(self):
        for w in self.frame_lista_scroll.winfo_children():
            w.destroy()
        self._todos_clientes = db_manager.obtener_clientes()
        self._renderizar_clientes(self._todos_clientes)

    def _renderizar_clientes(self, clientes):
        for w in self.frame_lista_scroll.winfo_children():
            w.destroy()
        for c in clientes:
            btn = ctk.CTkButton(
                self.frame_lista_scroll,
                text=c["nombre"],
                fg_color="transparent", hover_color=COLOR_HOVER,
                text_color=COLOR_TEXT, anchor="w", height=36,
                font=ctk.CTkFont(size=12),
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
            self.frame_crm.pack(fill="x", padx=10, pady=(0, 8), before=self.frame_hist_scroll)
        else:
            self.frame_crm.pack_forget()

        for w in self.frame_hist_scroll.winfo_children():
            w.destroy()
        pedidos = db_manager.obtener_pedidos(filtro_cliente_id=cliente_id)
        for p in pedidos:
            f = ctk.CTkFrame(self.frame_hist_scroll, fg_color="#252525", corner_radius=8)
            f.pack(fill="x", pady=3, padx=2)
            ctk.CTkLabel(f, text=f"{p.get('fecha','')}  –  {p.get('descripcion','')[:30]}",
                         font=ctk.CTkFont(size=11), text_color=COLOR_TEXT,
                         anchor="w").pack(side="left", padx=10, pady=6)
            ctk.CTkLabel(f, text=f"${p.get('precio_venta',0):.2f}",
                         font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_ACCENT,
                         anchor="e").pack(side="right", padx=10)

    def _nuevo_cliente(self):
        self._cliente_seleccionado = None
        for e in [self.ent_nombre, self.ent_email, self.ent_telefono,
                  self.ent_direccion, self.ent_notas]:
            e.delete(0, "end")

    def _guardar_cliente(self):
        nombre = self.ent_nombre.get().strip()
        if not nombre:
            messagebox.showwarning(T("warning"), T("clients_name_req"))
            return
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
        self._nuevo_cliente()
        self._cargar_clientes()

    def _eliminar_cliente(self):
        if not self._cliente_seleccionado:
            messagebox.showwarning(T("warning"), T("clients_select"))
            return
        if messagebox.askyesno(T("confirm"), T("clients_confirm_del")):
            db_manager.eliminar_cliente(self._cliente_seleccionado)
            self._nuevo_cliente()
            self._cargar_clientes()

    def _copiar_mensaje_crm(self):
        nombre_completo = self.ent_nombre.get().strip() or "amigo"
        nombre = nombre_completo.split()[0]
        texto = T("clients_crm_msg", name=nombre)
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.update()
        messagebox.showinfo(T("copied_msg"), T("clients_crm_copied"))
