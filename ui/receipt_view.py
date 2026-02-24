import customtkinter as ctk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path
import ctypes

from services.receipt_pdf_service import generate_receipt_pdf, list_receipts, open_receipt_pdf
from services.backup_service import create_manual_backup, get_latest_backups, restore_backup
from services.app_settings_service import get_saved_logo_path, save_logo_file, get_saved_city, set_saved_city


class ReceiptView(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.logo_path = get_saved_logo_path()
        self.default_city = get_saved_city()
        if self.logo_path and not Path(self.logo_path).exists():
            self.logo_path = ""

        self.pack(fill="both", expand=True)
        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=10, pady=8)
        self.container = container
        self.container.bind("<Configure>", self._update_responsive_layout)

        scroll_area = ctk.CTkScrollableFrame(container, fg_color="transparent")
        scroll_area.pack(fill="both", expand=True)

        content = ctk.CTkFrame(scroll_area)
        content.pack(fill="x", expand=True, padx=140, pady=(4, 8))
        self.content = content

        header_actions = ctk.CTkFrame(content, fg_color="transparent")
        header_actions.pack(fill="x", padx=12, pady=(2, 2))

        ctk.CTkButton(
            header_actions,
            text="Backup",
            height=28,
            width=96,
            font=("Arial", 12),
            fg_color="transparent",
            border_width=1,
            text_color=("#374151", "#D1D5DB"),
            command=self.open_backup_menu,
        ).pack(side="right")

        ctk.CTkLabel(content, text="Gerar Recibo", font=("Arial", 24, "bold")).pack(anchor="center", padx=12, pady=(8, 6))

        form = ctk.CTkFrame(content)
        form.pack(fill="x", padx=12, pady=(0, 8))

        self.client_name_entry = self._add_field(form, "Nome do Cliente")
        self.document_entry = self._add_field(form, "CPF / CNPJ")

        ctk.CTkLabel(form, text="Descrição do Serviço", font=("Arial", 14)).pack(anchor="w", padx=12, pady=(6, 2))
        self.description_entry = ctk.CTkTextbox(form, height=50)
        self.description_entry.pack(fill="x", padx=12, pady=(0, 6))

        self.amount_entry = self._add_field(form, "Valor do Recibo")

        pay_pix_row = ctk.CTkFrame(form, fg_color="transparent")
        pay_pix_row.pack(fill="x", padx=12, pady=(6, 6))
        self.pay_pix_row = pay_pix_row
        self.pay_pix_row.grid_columnconfigure(0, weight=2)
        self.pay_pix_row.grid_columnconfigure(1, weight=3)

        payment_col = ctk.CTkFrame(pay_pix_row, fg_color="transparent")
        payment_col.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.payment_col = payment_col

        ctk.CTkLabel(payment_col, text="Forma de Pagamento", font=("Arial", 14)).pack(anchor="w", pady=(0, 2))
        self.payment_method_option = ctk.CTkOptionMenu(
            payment_col,
            values=["Pix", "Dinheiro", "Cartão de Crédito", "Cartão de Débito", "Transferência", "Boleto"],
            command=lambda _value: self._sync_pix_controls(),
        )
        self.payment_method_option.pack(fill="x")
        self.payment_method_option.set("Pix")

        pix_col = ctk.CTkFrame(pay_pix_row, fg_color="transparent")
        pix_col.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.pix_col = pix_col

        ctk.CTkLabel(pix_col, text="Chave Pix", font=("Arial", 14)).pack(anchor="w", pady=(0, 2))
        self.pix_key_entry = ctk.CTkEntry(pix_col)
        self.pix_key_entry.pack(fill="x")

        self.include_logo_var = ctk.BooleanVar(value=False)
        ctk.CTkLabel(form, text="Preferências", font=("Arial", 13, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
        logo_row = ctk.CTkFrame(form, fg_color="transparent")
        logo_row.pack(fill="x", padx=12, pady=(2, 6))

        self.include_logo_check = ctk.CTkCheckBox(
            logo_row,
            text="Exibir minha logo nos recibos",
            variable=self.include_logo_var,
            command=self._sync_logo_controls,
        )
        self.include_logo_check.pack(side="left")

        self.logo_button = ctk.CTkButton(logo_row, text="Definir Logo", width=150, command=self._select_logo)
        self.logo_button.pack(side="left", padx=(10, 0))

        self.logo_name_label = ctk.CTkLabel(form, text="Logo não definida", font=("Arial", 12), text_color="gray")
        self.logo_name_label.pack(anchor="w", padx=12, pady=(0, 6))
        self._refresh_logo_label()

        extras = ctk.CTkFrame(form, fg_color="transparent")
        extras.pack(fill="x", padx=12, pady=(2, 4))
        self.city_entry = ctk.CTkEntry(extras, placeholder_text="Cidade (ex.: Curitiba)")
        self.city_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.city_button = ctk.CTkButton(
            extras,
            text="Fixar Cidade",
            width=106,
            height=30,
            command=self.save_default_city,
        )
        self.city_button.pack(side="left", padx=(0, 8))
        self.issuer_name_entry = ctk.CTkEntry(extras, placeholder_text="Nome de quem assina")
        self.issuer_name_entry.pack(side="left", fill="x", expand=True)
        if self.default_city:
            self.city_entry.insert(0, self.default_city)
        self._sync_city_button()

        self.status_label = ctk.CTkLabel(content, text="", font=("Arial", 13), text_color="red", corner_radius=8, fg_color="transparent")
        self.status_label.pack(anchor="center", padx=12, pady=(2, 4))

        buttons = ctk.CTkFrame(content, fg_color="transparent")
        buttons.pack(anchor="center", pady=(2, 6))

        ctk.CTkButton(buttons, text="Gerar Recibo em PDF", height=36, command=self.generate_receipt).pack(side="left")
        ctk.CTkButton(buttons, text="Histórico de Recibos", height=36, fg_color="transparent", text_color=("black"), border_width=1, command=self.show_history).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            buttons,
            text="Limpar",
            height=36,
            width=96,
            fg_color="transparent",
            border_width=1,
            text_color=("#374151", "#D1D5DB"),
            command=self.clear_form,
        ).pack(side="left", padx=(8, 0))

        self._bind_masks()
        self._sync_logo_controls()
        self._sync_pix_controls()
        self._update_responsive_layout()

    def _add_field(self, parent, label):
        ctk.CTkLabel(parent, text=label, font=("Arial", 14)).pack(anchor="w", padx=12, pady=(6, 2))
        entry = ctk.CTkEntry(parent)
        entry.pack(fill="x", padx=12, pady=(0, 6))
        return entry

    def _bind_masks(self):
        self.document_entry.bind("<KeyRelease>", self._on_document_keyrelease)
        self.amount_entry.bind("<KeyRelease>", self._on_amount_keyrelease)

    def _refresh_logo_label(self):
        if not self.logo_path:
            self.logo_name_label.configure(text="Logo não definida", text_color="red")
            return

        if not Path(self.logo_path).exists():
            self.logo_path = ""
            self.logo_name_label.configure(text="Logo não definida", text_color="red")
            return

        self.logo_name_label.configure(text="Logo definida", text_color="green")

    def _on_document_keyrelease(self, _event=None):
        raw = self.document_entry.get()
        digits = "".join(char for char in raw if char.isdigit())[:14]
        formatted = self._format_cpf_cnpj(digits)
        self.document_entry.delete(0, "end")
        self.document_entry.insert(0, formatted)

    def _on_amount_keyrelease(self, _event=None):
        raw = self.amount_entry.get()
        digits = "".join(char for char in raw if char.isdigit())

        if not digits:
            self.amount_entry.delete(0, "end")
            return

        value = int(digits) / 100
        formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.amount_entry.delete(0, "end")
        self.amount_entry.insert(0, formatted)

    def _format_cpf_cnpj(self, digits):
        if len(digits) <= 11:
            p1 = digits[:3]
            p2 = digits[3:6]
            p3 = digits[6:9]
            p4 = digits[9:11]
            if len(digits) <= 3:
                return p1
            if len(digits) <= 6:
                return f"{p1}.{p2}"
            if len(digits) <= 9:
                return f"{p1}.{p2}.{p3}"
            return f"{p1}.{p2}.{p3}-{p4}"

        p1 = digits[:2]
        p2 = digits[2:5]
        p3 = digits[5:8]
        p4 = digits[8:12]
        p5 = digits[12:14]
        if len(digits) <= 2:
            return p1
        if len(digits) <= 5:
            return f"{p1}.{p2}"
        if len(digits) <= 8:
            return f"{p1}.{p2}.{p3}"
        if len(digits) <= 12:
            return f"{p1}.{p2}.{p3}/{p4}"
        return f"{p1}.{p2}.{p3}/{p4}-{p5}"

    def clear_form(self):
        self.client_name_entry.delete(0, "end")
        self.document_entry.delete(0, "end")
        self.description_entry.delete("1.0", "end")
        self.amount_entry.delete(0, "end")

        self.payment_method_option.set("Pix")

        self.pix_key_entry.configure(state="normal")
        self.pix_key_entry.delete(0, "end")

        self.include_logo_var.set(False)

        self.city_entry.delete(0, "end")
        if self.default_city:
            self.city_entry.insert(0, self.default_city)
        self.issuer_name_entry.delete(0, "end")

        self.show_feedback("", "green")
        self._sync_logo_controls()
        self._sync_pix_controls()

    def _sync_pix_controls(self):
        pix_selected = self.payment_method_option.get().lower() == "pix"
        if pix_selected:
            self.pix_key_entry.configure(state="normal")
        else:
            self.pix_key_entry.delete(0, "end")
            self.pix_key_entry.configure(state="disabled")

    def _sync_logo_controls(self):
        self.logo_button.configure(state="normal")

    def _select_logo(self):
        selected = filedialog.askopenfilename(
            title="Selecionar logo",
            filetypes=[("Imagens", "*.png;*.jpg;*.jpeg")],
        )
        if selected:
            if Path(selected).suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                self.show_feedback("Selecione uma logo no formato .png, .jpg ou .jpeg", "#DC2626")
                return
            try:
                self.logo_path = save_logo_file(selected)
                self._refresh_logo_label()
                self.show_feedback("Logo definida com sucesso.", "#16A34A")
            except Exception as exc:
                self.show_feedback(f"Falha ao definir logo: {exc}", "#DC2626")

    def _collect_data(self):
        return {
            "client_name": self.client_name_entry.get(),
            "cpf_cnpj": self.document_entry.get(),
            "description": self.description_entry.get("1.0", "end"),
            "amount": self.amount_entry.get(),
            "payment_method": self.payment_method_option.get(),
            "pix_key": self.pix_key_entry.get(),
            "include_logo": self.include_logo_var.get(),
            "logo_path": self.logo_path,
            "city": self.city_entry.get(),
            "issuer_name": self.issuer_name_entry.get(),
        }

    def generate_receipt(self):
        self.show_feedback("", "green")
        if self.include_logo_var.get() and not self.logo_path:
            self.show_feedback("Defina uma logo primeiro para usar no recibo.", "#DC2626")
            return

        try:
            report_path = generate_receipt_pdf(self._collect_data())
            open_receipt_pdf(report_path)
            self.show_feedback("Recibo gerado com sucesso.", "#16A34A")
        except Exception as exc:
            self.show_feedback(str(exc), "#DC2626")

    def show_history(self):
        history_window = ctk.CTkToplevel(self)
        history_window.title("Histórico de Recibos")
        history_window.geometry("860x420")
        self._center_toplevel_on_active_monitor(history_window, 860, 420)
        history_window.grab_set()

        ctk.CTkLabel(history_window, text="Histórico de Recibos", font=("Arial", 22, "bold")).pack(anchor="w", padx=18, pady=(16, 8))

        tree_frame = ctk.CTkFrame(history_window)
        tree_frame.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        columns = ("Número", "Cliente", "Valor", "Pagamento", "Data", "Arquivo")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, anchor="center")

        tree.column("Número", width=70, anchor="center")
        tree.column("Cliente", width=190, anchor="w")
        tree.column("Valor", width=100, anchor="e")
        tree.column("Pagamento", width=120, anchor="center")
        tree.column("Data", width=140, anchor="center")
        tree.column("Arquivo", width=220, anchor="w")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        rows = list_receipts(limit=300)
        for row in rows:
            file_name = str(row["pdf_path"]).replace("\\", "/").split("/")[-1]
            tree.insert(
                "",
                "end",
                values=(
                    row["id"],
                    row["client_name"],
                    self._format_currency(row["amount"]),
                    row["payment_method"],
                    row["created_at"],
                    file_name,
                ),
                tags=(row["pdf_path"],),
            )

        def open_selected(_event=None):
            selected = tree.selection()
            if not selected:
                return
            item_id = selected[0]
            tags = tree.item(item_id, "tags")
            if tags:
                open_receipt_pdf(tags[0])

        tree.bind("<Double-1>", open_selected)

        actions = ctk.CTkFrame(history_window, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkButton(actions, text="Abrir Selecionado", command=open_selected).pack(side="left")
        ctk.CTkButton(actions, text="Fechar", command=history_window.destroy).pack(side="right")

        history_window.after(
            0,
            lambda: self._center_toplevel_on_active_monitor(
                history_window,
                history_window.winfo_width(),
                history_window.winfo_height(),
            ),
        )

    def _format_currency(self, value):
        amount = float(value or 0)
        return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def show_feedback(self, message, color):
        self.status_label.configure(text=message, text_color=color)

    def _update_responsive_layout(self, _event=None):
        if not hasattr(self, "content"):
            return

        width = self.container.winfo_width() if hasattr(self, "container") else self.winfo_width()
        target_width = min(980, max(680, width - 120))
        horizontal_pad = max(12, (width - target_width) // 2)
        self.content.pack_configure(padx=horizontal_pad)

        if width < 1020:
            self.payment_col.grid_configure(row=0, column=0, columnspan=2, padx=(0, 0), pady=(0, 6))
            self.pix_col.grid_configure(row=1, column=0, columnspan=2, padx=(0, 0), pady=(0, 0))
            self.pay_pix_row.grid_columnconfigure(0, weight=1)
            self.pay_pix_row.grid_columnconfigure(1, weight=1)
        else:
            self.payment_col.grid_configure(row=0, column=0, columnspan=1, padx=(0, 6), pady=(0, 0))
            self.pix_col.grid_configure(row=0, column=1, columnspan=1, padx=(6, 0), pady=(0, 0))
            self.pay_pix_row.grid_columnconfigure(0, weight=2)
            self.pay_pix_row.grid_columnconfigure(1, weight=3)

    def save_default_city(self):
        city = " ".join(self.city_entry.get().strip().split())
        if not city:
            self.show_feedback("Informe uma cidade para fixar.", "#DC2626")
            return

        set_saved_city(city)
        self.default_city = city
        self.city_entry.delete(0, "end")
        self.city_entry.insert(0, city)
        self._sync_city_button()
        self.show_feedback(f"Cidade padrão definida: {city}", "#16A34A")

    def unset_default_city(self):
        set_saved_city("")
        self.default_city = ""
        self.city_entry.delete(0, "end")
        self._sync_city_button()
        self.show_feedback("Cidade padrão removida.", "#16A34A")

    def _sync_city_button(self):
        if self.default_city:
            self.city_button.configure(text="Desfixar Cidade", command=self.unset_default_city)
            return
        self.city_button.configure(text="Fixar Cidade", command=self.save_default_city)

    def create_backup_now(self):
        try:
            backup_path = create_manual_backup(max_files=30)
            self.show_feedback(f"Backup criado: {backup_path}", "#16A34A")
        except Exception as exc:
            self.show_feedback(f"Falha ao criar backup: {exc}", "#DC2626")

    def restore_latest_backup(self):
        backups = get_latest_backups(limit=1)
        if not backups:
            self.show_feedback("Nenhum backup encontrado.", "#DC2626")
            return

        latest = backups[0]
        confirm = messagebox.askyesno(
            "Restaurar Backup",
            (
                "Deseja restaurar o último backup?\n\n"
                f"Arquivo: {latest['name']}\n"
                f"Data: {latest['modified_at']}\n\n"
                "Isso substitui os dados atuais."
            ),
        )
        if not confirm:
            return

        try:
            restore_backup(latest["path"])
            self.show_feedback("Backup restaurado com sucesso.", "#16A34A")
        except Exception as exc:
            self.show_feedback(f"Falha ao restaurar backup: {exc}", "#DC2626")

    def open_backup_menu(self):
        menu_window = ctk.CTkToplevel(self)
        menu_window.title("Backup")
        menu_window.geometry("290x170")
        menu_window.resizable(False, False)
        menu_window.attributes("-topmost", True)
        menu_window.grab_set()
        self._center_toplevel_on_active_monitor(menu_window, 290, 170)

        ctk.CTkLabel(menu_window, text="Menu de Backup", font=("Arial", 18, "bold")).pack(pady=(14, 10))
        ctk.CTkButton(menu_window, text="Criar Backup", width=180, command=lambda: self._run_backup_action(menu_window, self.create_backup_now)).pack(pady=(0, 8))
        ctk.CTkButton(menu_window, text="Restaurar Último", width=180, command=lambda: self._run_backup_action(menu_window, self.restore_latest_backup)).pack(pady=(0, 8))
        ctk.CTkButton(menu_window, text="Fechar", width=180, fg_color="transparent", text_color="black", border_width=1, command=menu_window.destroy).pack()

    def _run_backup_action(self, menu_window, action):
        menu_window.destroy()
        action()

    def _center_toplevel_on_active_monitor(self, window, width, height):
        window.update_idletasks()

        try:
            user32 = ctypes.windll.user32

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("rcMonitor", RECT),
                    ("rcWork", RECT),
                    ("dwFlags", ctypes.c_ulong),
                ]

            point = POINT()
            user32.GetCursorPos(ctypes.byref(point))

            monitor = user32.MonitorFromPoint(point, 2)
            monitor_info = MONITORINFO()
            monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
            user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info))

            area = monitor_info.rcWork
            x = area.left + max(0, ((area.right - area.left) - width) // 2)
            y = area.top + max(0, ((area.bottom - area.top) - height) // 2)
            window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            x = max(0, (window.winfo_screenwidth() - width) // 2)
            y = max(0, (window.winfo_screenheight() - height) // 2)
            window.geometry(f"{width}x{height}+{x}+{y}")
