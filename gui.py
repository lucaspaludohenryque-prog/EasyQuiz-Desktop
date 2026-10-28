"""
Interface Gráfica Moderna (GUI) - Mastering Study Quiz
Construída com CustomTkinter, padrão Tema Claro (Clean White) com alternância rápida para Dark Mode,
sidebar minimalista, monitor do Cérebro em Tempo Real e galeria de cards com filtro e busca.
"""

import os
import datetime
import tkinter as tk
from typing import Optional, List, Dict
from PIL import Image
import customtkinter as ctk

from config_manager import ConfigManager
from ai_vision import AIVisionService
from cerebro_manager import CerebroManager, CerebroItem
from automation import AutomationEngine
from overlay import ScreenAreaSelector, PointSelector

# Configuração inicial: Modo Claro padrão por especificação do projeto
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class MasteringStudyQuizGUI(ctk.CTk):
    """Janela principal do aplicativo Mastering Study Quiz."""

    def __init__(
        self,
        config_manager: ConfigManager,
        ai_service: AIVisionService,
        cerebro_manager: CerebroManager
    ):
        super().__init__()

        self.config_manager = config_manager
        self.ai_service = ai_service
        self.cerebro_manager = cerebro_manager

        # Motor de automação RPA com callbacks para a GUI
        self.engine = AutomationEngine(
            config_manager=self.config_manager,
            ai_service=self.ai_service,
            cerebro_manager=self.cerebro_manager,
            log_callback=self.enqueue_log,
            status_callback=self.update_status_badge,
            live_cerebro_callback=self.update_live_cerebro_card
        )

        # Configurações da Janela
        self.title("Mastering Study Quiz - Automação Inteligente & Memória Visual")
        self.geometry("1160x820")
        self.minsize(1040, 740)

        # Configura grid mestre (Sidebar fixa + Conteúdo dinâmico)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Variáveis de controle de visualização
        self.current_theme = ctk.StringVar(value="Light")
        self.search_query_var = ctk.StringVar()
        self.selected_category_filter = "Todos"
        self.cached_images: Dict[str, ctk.CTkImage] = {}

        # Construção da Interface
        self._build_sidebar()
        self._build_content_area()
        self._setup_hotkeys()
        self._load_saved_settings()

        # Seleciona a aba padrão Dashboard
        self._switch_tab("dashboard")

        # Protocolo de encerramento seguro
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.enqueue_log("Mastering Study Quiz inicializado com sucesso.", "SUCCESS")
        self.enqueue_log("Padrão: Tema Claro (Clean White). Atalhos: [F8] Iniciar/Pausar | [ESC] Parar.", "INFO")

    # =========================================================================
    # BARRA LATERAL (SIDEBAR DE NAVEGAÇÃO)
    # =========================================================================
    def _build_sidebar(self) -> None:
        """Cria a barra lateral de navegação com logotipo, botões de abas e seletor de tema."""
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Logo / Título
        logo_box = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        logo_box.grid(row=0, column=0, padx=20, pady=(24, 16), sticky="w")

        lbl_app_name = ctk.CTkLabel(
            logo_box,
            text="MASTERING",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#1E88E5"
        )
        lbl_app_name.pack(anchor="w")

        lbl_app_sub = ctk.CTkLabel(
            logo_box,
            text="Study Quiz Desktop",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#546E7A"
        )
        lbl_app_sub.pack(anchor="w")

        # Botões de Navegação
        self.btn_nav_dash = ctk.CTkButton(
            self.sidebar_frame,
            text="⚡  Dashboard",
            height=40,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda: self._switch_tab("dashboard")
        )
        self.btn_nav_dash.grid(row=1, column=0, padx=16, pady=6, sticky="ew")

        self.btn_nav_cerebro = ctk.CTkButton(
            self.sidebar_frame,
            text="🧠  Explorar Cérebro",
            height=40,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda: self._switch_tab("cerebro")
        )
        self.btn_nav_cerebro.grid(row=2, column=0, padx=16, pady=6, sticky="ew")

        self.btn_nav_config = ctk.CTkButton(
            self.sidebar_frame,
            text="⚙️  Configurações",
            height=40,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda: self._switch_tab("config")
        )
        self.btn_nav_config.grid(row=3, column=0, padx=16, pady=6, sticky="ew")

        # Área Inferior da Sidebar: Alternador de Tema Claro / Escuro
        theme_box = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        theme_box.grid(row=5, column=0, padx=16, pady=20, sticky="ew")

        ctk.CTkLabel(
            theme_box,
            text="Aparência Visual:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", pady=(0, 6))

        self.theme_switch = ctk.CTkSwitch(
            theme_box,
            text="Modo Escuro",
            command=self._on_theme_toggle,
            variable=self.current_theme,
            onvalue="Dark",
            offvalue="Light"
        )
        self.theme_switch.pack(anchor="w")

    # =========================================================================
    # ÁREA DE CONTEÚDO DINÂMICA
    # =========================================================================
    def _build_content_area(self) -> None:
        """Cria os contêineres de cada uma das 3 abas principais."""
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self._build_dashboard_tab()
        self._build_cerebro_tab()
        self._build_config_tab()

    def _switch_tab(self, tab_id: str) -> None:
        """Alterna a exibição para a aba desejada e ajusta as cores dos botões de navegação."""
        self.tab_dashboard.grid_remove()
        self.tab_cerebro.grid_remove()
        self.tab_config.grid_remove()

        # Reseta estilos dos botões
        inactive_color = "transparent"
        active_color = ("#E3F2FD", "#1E293B")
        text_active = ("#1565C0", "#60A5FA")
        text_inactive = ("#374151", "#94A3B8")

        self.btn_nav_dash.configure(fg_color=inactive_color, text_color=text_inactive)
        self.btn_nav_cerebro.configure(fg_color=inactive_color, text_color=text_inactive)
        self.btn_nav_config.configure(fg_color=inactive_color, text_color=text_inactive)

        if tab_id == "dashboard":
            self.tab_dashboard.grid(row=0, column=0, sticky="nsew")
            self.btn_nav_dash.configure(fg_color=active_color, text_color=text_active)
        elif tab_id == "cerebro":
            self.tab_cerebro.grid(row=0, column=0, sticky="nsew")
            self.btn_nav_cerebro.configure(fg_color=active_color, text_color=text_active)
            self._refresh_cerebro_gallery()
        elif tab_id == "config":
            self.tab_config.grid(row=0, column=0, sticky="nsew")
            self.btn_nav_config.configure(fg_color=active_color, text_color=text_active)

    # =========================================================================
    # ABA 1: DASHBOARD & MONITOR AO VIVO DO CÉREBRO (SPLIT-SCREEN)
    # =========================================================================
    def _build_dashboard_tab(self) -> None:
        """Constrói a visualização dividida: Controles de RPA à esquerda e Cérebro Ao Vivo à direita."""
        self.tab_dashboard = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.tab_dashboard.grid_columnconfigure(0, weight=4)  # Coluna de Controles (40%)
        self.tab_dashboard.grid_columnconfigure(1, weight=6)  # Monitor do Cérebro (60%)
        self.tab_dashboard.grid_rowconfigure(1, weight=1)

        # Topo: Cabeçalho com Status Badge
        top_bar = ctk.CTkFrame(self.tab_dashboard, corner_radius=10)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        ctk.CTkLabel(
            top_bar,
            text="PAINEL DE AUTOMAÇÃO E MONITORAMENTO EM TEMPO REAL",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(side="left", padx=16, pady=12)

        self.status_badge = ctk.CTkLabel(
            top_bar,
            text="● PARADO",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#EF4444",
            fg_color=("#FEE2E2", "#3B1E1E"),
            corner_radius=8,
            padx=14,
            pady=6
        )
        self.status_badge.pack(side="right", padx=16, pady=10)

        # LADO ESQUERDO: Controles de Calibração, Execução e Logs
        left_col = ctk.CTkScrollableFrame(self.tab_dashboard, fg_color="transparent")
        left_col.grid(row=1, column=0, sticky="nsew", padx=(0, 8))

        # Card de Controles de Execução
        ctrl_card = ctk.CTkFrame(left_col, corner_radius=10)
        ctrl_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            ctrl_card,
            text="🎮 Controles da Automação",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=14, pady=(10, 6))

        btn_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 8))
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.btn_start = ctk.CTkButton(
            btn_row,
            text="▶ Iniciar (F8)",
            command=self._cmd_start,
            fg_color="#16A34A",
            hover_color="#15803D",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.btn_start.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.btn_stop = ctk.CTkButton(
            btn_row,
            text="⏹ Parar (ESC)",
            command=self._cmd_stop,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.btn_stop.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # Card de Calibração de Tela
        calib_card = ctk.CTkFrame(left_col, corner_radius=10)
        calib_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            calib_card,
            text="📐 Calibração de Regiões",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=14, pady=(10, 6))

        btn_area = ctk.CTkButton(
            calib_card,
            text="🔍 Selecionar Área do Quiz",
            command=self._start_area_selection,
            fg_color="#2563EB",
            hover_color="#1D4ED8"
        )
        btn_area.pack(fill="x", padx=14, pady=4)

        self.lbl_area_status = ctk.CTkLabel(
            calib_card,
            text="Área: Não definida",
            font=ctk.CTkFont(size=11),
            text_color="#F59E0B"
        )
        self.lbl_area_status.pack(anchor="w", padx=16, pady=(0, 6))

        btn_next = ctk.CTkButton(
            calib_card,
            text="🎯 Mapear Botão Próximo",
            command=self._start_next_button_selection,
            fg_color="#4F46E5",
            hover_color="#4338CA"
        )
        btn_next.pack(fill="x", padx=14, pady=4)

        self.lbl_next_status = ctk.CTkLabel(
            calib_card,
            text="Botão Próximo: Não definido",
            font=ctk.CTkFont(size=11),
            text_color="#64748B"
        )
        self.lbl_next_status.pack(anchor="w", padx=16, pady=(0, 10))

        # Temporização
        time_card = ctk.CTkFrame(left_col, corner_radius=10)
        time_card.pack(fill="x", pady=(0, 10))

        delay_hdr = ctk.CTkFrame(time_card, fg_color="transparent")
        delay_hdr.pack(fill="x", padx=14, pady=(8, 0))

        ctk.CTkLabel(delay_hdr, text="Espera antes de avançar:").pack(side="left")
        self.lbl_delay_val = ctk.CTkLabel(delay_hdr, text="2.5s", font=ctk.CTkFont(weight="bold"))
        self.lbl_delay_val.pack(side="right")

        self.slider_delay = ctk.CTkSlider(
            time_card,
            from_=0.5,
            to=8.0,
            number_of_steps=75,
            command=self._on_delay_change
        )
        self.slider_delay.pack(fill="x", padx=14, pady=(2, 12))

        # Console de Logs Compacto
        log_card = ctk.CTkFrame(left_col, corner_radius=10)
        log_card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            log_card,
            text="📜 Log de Passos",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=14, pady=(8, 4))

        self.log_textbox = ctk.CTkTextbox(
            log_card,
            height=140,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
            corner_radius=8
        )
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # LADO DIREITO: CÉREBRO EM TEMPO REAL (LIVE MONITOR)
        right_col = ctk.CTkFrame(self.tab_dashboard, corner_radius=12)
        right_col.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right_col.grid_rowconfigure(2, weight=1)
        right_col.grid_columnconfigure(0, weight=1)

        # Header do Cérebro em Tempo Real
        live_header = ctk.CTkFrame(right_col, fg_color="transparent")
        live_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            live_header,
            text="🧠 Monitor do Cérebro em Tempo Real",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#0284C7"
        ).pack(side="left")

        self.lbl_total_cerebro = ctk.CTkLabel(
            live_header,
            text="Total na Memória: 0",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#64748B"
        )
        self.lbl_total_cerebro.pack(side="right")

        # Badge de Classificação em Destaque
        badge_row = ctk.CTkFrame(right_col, fg_color="transparent")
        badge_row.grid(row=1, column=0, sticky="ew", padx=16, pady=4)

        ctk.CTkLabel(badge_row, text="Elemento Visual Detectado:", font=ctk.CTkFont(size=12)).pack(side="left")

        self.badge_categoria = ctk.CTkLabel(
            badge_row,
            text="[ AGUARDANDO ESCANEAMENTO ]",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#059669",
            fg_color=("#D1FAE5", "#064E3B"),
            corner_radius=8,
            padx=12,
            pady=4
        )
        self.badge_categoria.pack(side="left", padx=10)

        # Container Principal de Exibição Ao Vivo
        live_body = ctk.CTkScrollableFrame(right_col, fg_color="transparent")
        live_body.grid(row=2, column=0, sticky="nsew", padx=16, pady=(4, 14))

        # Imagem Recortada em Tempo Real
        self.live_img_container = ctk.CTkFrame(
            live_body,
            height=240,
            fg_color=("#F1F5F9", "#1E293B"),
            corner_radius=10
        )
        self.live_img_container.pack(fill="x", pady=(0, 10))

        self.lbl_live_image = ctk.CTkLabel(
            self.live_img_container,
            text="🖼️ O recorte do elemento visual analisado pela IA aparecerá aqui em tempo real.",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_live_image.pack(expand=True, fill="both", padx=12, pady=12)

        # Contexto Explicativo da Imagem
        ctk.CTkLabel(
            live_body,
            text="💡 Contexto Educacional da Imagem:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", pady=(4, 2))

        self.txt_live_contexto = ctk.CTkTextbox(
            live_body,
            height=65,
            font=ctk.CTkFont(size=12),
            wrap="word",
            corner_radius=8
        )
        self.txt_live_contexto.pack(fill="x", pady=(0, 10))
        self.txt_live_contexto.insert("1.0", "A IA descreverá automaticamente gráficos, fórmulas ou figuras aqui...")

        # Enunciado Identificado
        ctk.CTkLabel(
            live_body,
            text="📝 Enunciado Identificado:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", pady=(4, 2))

        self.txt_live_pergunta = ctk.CTkTextbox(
            live_body,
            height=65,
            font=ctk.CTkFont(size=12),
            wrap="word",
            corner_radius=8
        )
        self.txt_live_pergunta.pack(fill="x", pady=(0, 10))
        self.txt_live_pergunta.insert("1.0", "A pergunta extraída aparecerá aqui...")

        # Alternativa Clicada
        ans_card = ctk.CTkFrame(live_body, fg_color=("#ECFDF5", "#064E3B"), corner_radius=8)
        ans_card.pack(fill="x", pady=(4, 0))

        ctk.CTkLabel(
            ans_card,
            text="✅ Alternativa Clicada:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#047857"
        ).pack(side="left", padx=12, pady=10)

        self.lbl_live_resposta = ctk.CTkLabel(
            ans_card,
            text="Nenhuma resposta selecionada ainda.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#065F46"
        )
        self.lbl_live_resposta.pack(side="left", padx=6, pady=10)

    # =========================================================================
    # ABA 2: EXPLORAR CÉREBRO (GALERIA INTERATIVA & BUSCA)
    # =========================================================================
    def _build_cerebro_tab(self) -> None:
        """Constrói a galeria interativa com barra de busca, filtros rápidos e grade rolável."""
        self.tab_cerebro = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.tab_cerebro.grid_rowconfigure(2, weight=1)
        self.tab_cerebro.grid_columnconfigure(0, weight=1)

        # Topo: Barra de Busca
        search_card = ctk.CTkFrame(self.tab_cerebro, corner_radius=10)
        search_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(
            search_card,
            text="🔎 Buscar no Cérebro:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left", padx=14, pady=10)

        self.entry_search = ctk.CTkEntry(
            search_card,
            placeholder_text="Digite 'Gráfico', 'Equação' ou palavra-chave da matéria...",
            textvariable=self.search_query_var,
            font=ctk.CTkFont(size=13)
        )
        self.entry_search.pack(side="left", fill="x", expand=True, padx=8, pady=10)
        self.entry_search.bind("<KeyRelease>", lambda e: self._refresh_cerebro_gallery())

        btn_search = ctk.CTkButton(
            search_card,
            text="Pesquisar",
            width=100,
            command=self._refresh_cerebro_gallery
        )
        btn_search.pack(side="left", padx=(0, 14), pady=10)

        # Filtros Rápidos por Categoria
        filters_bar = ctk.CTkFrame(self.tab_cerebro, fg_color="transparent")
        filters_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.filter_buttons: List[ctk.CTkButton] = []
        categorias_filtro = ["Todos", "Gráfico", "Tabela", "Diagrama", "Fórmula", "Texto Puro"]

        for cat in categorias_filtro:
            btn_f = ctk.CTkButton(
                filters_bar,
                text=cat,
                height=32,
                corner_radius=16,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=("#2563EB", "#1D4ED8") if cat == "Todos" else ("#E2E8F0", "#334155"),
                text_color="#FFFFFF" if cat == "Todos" else ("#1E293B", "#F8FAFC"),
                command=lambda c=cat: self._set_category_filter(c)
            )
            btn_f.pack(side="left", padx=4)
            self.filter_buttons.append(btn_f)

        # Grade Rolável de Cards do Cérebro
        self.gallery_scroll = ctk.CTkScrollableFrame(self.tab_cerebro, corner_radius=12)
        self.gallery_scroll.grid(row=2, column=0, sticky="nsew")
        self.gallery_scroll.grid_columnconfigure((0, 1), weight=1)

    def _set_category_filter(self, category: str) -> None:
        """Aplica filtro rápido de categoria e redesenha a galeria."""
        self.selected_category_filter = category
        for btn in self.filter_buttons:
            if btn.cget("text") == category:
                btn.configure(fg_color=("#2563EB", "#1D4ED8"), text_color="#FFFFFF")
            else:
                btn.configure(fg_color=("#E2E8F0", "#334155"), text_color=("#1E293B", "#F8FAFC"))
        self._refresh_cerebro_gallery()

    def _refresh_cerebro_gallery(self) -> None:
        """Recarrega os cards na aba 'Explorar Cérebro'."""
        for widget in self.gallery_scroll.winfo_children():
            widget.destroy()

        query = self.search_query_var.get()
        itens = self.cerebro_manager.search_items(
            query=query,
            categoria_filter=self.selected_category_filter
        )

        if not itens:
            empty_box = ctk.CTkFrame(self.gallery_scroll, fg_color="transparent")
            empty_box.grid(row=0, column=0, columnspan=2, pady=40)
            ctk.CTkLabel(
                empty_box,
                text="🧠 Nenhum item encontrado no Cérebro para este filtro.",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#94A3B8"
            ).pack()
            return

        for idx, item in enumerate(itens):
            row_idx = idx // 2
            col_idx = idx % 2
            self._render_cerebro_card(self.gallery_scroll, item, row_idx, col_idx)

    def _render_cerebro_card(self, parent: ctk.CTkScrollableFrame, item: CerebroItem, row: int, col: int) -> None:
        """Renderiza um card individual do Cérebro com miniatura, badge e resumo."""
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        # Cabeçalho do Card: Badge + Data
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 4))

        badge = ctk.CTkLabel(
            hdr,
            text=f" {item.categoria.upper()} ",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#DBEAFE", "#1E3A8A"),
            text_color="#1D4ED8",
            corner_radius=6
        )
        badge.pack(side="left")

        ctk.CTkLabel(
            hdr,
            text=item.data_hora.split(" ")[1] if " " in item.data_hora else item.data_hora,
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        ).pack(side="right")

        # Thumbnail da Imagem (se houver)
        if item.caminho_thumbnail and os.path.exists(item.caminho_thumbnail):
            try:
                if item.caminho_thumbnail not in self.cached_images:
                    pil_img = Image.open(item.caminho_thumbnail)
                    self.cached_images[item.caminho_thumbnail] = ctk.CTkImage(
                        light_image=pil_img,
                        dark_image=pil_img,
                        size=(240, 150)
                    )
                ctk_img = self.cached_images[item.caminho_thumbnail]
                img_lbl = ctk.CTkLabel(card, image=ctk_img, text="")
                img_lbl.pack(pady=4)
            except Exception:
                pass

        # Texto da Pergunta
        pergunta_preview = item.pergunta[:90] + ("..." if len(item.pergunta) > 90 else "")
        ctk.CTkLabel(
            card,
            text=pergunta_preview,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            justify="left",
            wraplength=340
        ).pack(fill="x", padx=10, pady=2)

        # Resposta Correta
        ans_box = ctk.CTkFrame(card, fg_color=("#F0FDF4", "#064E3B"), corner_radius=6)
        ans_box.pack(fill="x", padx=10, pady=(4, 8))

        ctk.CTkLabel(
            ans_box,
            text=f"✔ {item.resposta_correta}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#047857",
            anchor="w",
            justify="left",
            wraplength=330
        ).pack(fill="x", padx=8, pady=4)

        # Botão para Expandir Detalhes
        btn_details = ctk.CTkButton(
            card,
            text="Ver Detalhes do Estudo",
            height=28,
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            command=lambda i=item: self._show_card_details_modal(i)
        )
        btn_details.pack(fill="x", padx=10, pady=(0, 10))

    def _show_card_details_modal(self, item: CerebroItem) -> None:
        """Abre uma janela modal detalhada com a imagem ampliada e contexto completo."""
        modal = ctk.CTkToplevel(self)
        modal.title(f"Cérebro - Detalhes da Questão #{item.id}")
        modal.geometry("700x720")
        modal.minsize(580, 600)
        modal.attributes("-topmost", True)

        scroll = ctk.CTkScrollableFrame(modal)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # Categoria Badge
        ctk.CTkLabel(
            scroll,
            text=f"[ {item.categoria.upper()} ] - {item.data_hora}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2563EB"
        ).pack(anchor="w", pady=(0, 10))

        # Imagem em tamanho maior
        if item.caminho_imagem and os.path.exists(item.caminho_imagem):
            try:
                orig_img = Image.open(item.caminho_imagem)
                w, h = orig_img.size
                ratio = min(620 / max(1, w), 340 / max(1, h))
                disp_w = max(50, int(w * ratio))
                disp_h = max(50, int(h * ratio))

                expanded_ctk_img = ctk.CTkImage(
                    light_image=orig_img,
                    dark_image=orig_img,
                    size=(disp_w, disp_h)
                )
                img_lbl = ctk.CTkLabel(scroll, image=expanded_ctk_img, text="")
                img_lbl.pack(pady=10)
            except Exception as e:
                ctk.CTkLabel(scroll, text=f"Erro ao carregar imagem: {e}").pack()

        # Contexto Educacional
        ctk.CTkLabel(scroll, text="💡 Contexto da Imagem / Figura:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(6, 2))
        ctx_box = ctk.CTkTextbox(scroll, height=80, wrap="word")
        ctx_box.pack(fill="x", pady=(0, 10))
        ctx_box.insert("1.0", item.contexto_explicativo or "Sem contexto específico registrado.")
        ctx_box.configure(state="disabled")

        # Pergunta Completa
        ctk.CTkLabel(scroll, text="📝 Enunciado Completo:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(6, 2))
        q_box = ctk.CTkTextbox(scroll, height=90, wrap="word")
        q_box.pack(fill="x", pady=(0, 10))
        q_box.insert("1.0", item.pergunta)
        q_box.configure(state="disabled")

        # Alternativa
        ctk.CTkLabel(scroll, text="✅ Alternativa Correta:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(6, 2))
        ans_lbl = ctk.CTkLabel(
            scroll,
            text=item.resposta_correta,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#059669",
            fg_color=("#D1FAE5", "#064E3B"),
            corner_radius=8,
            padx=12,
            pady=8
        )
        ans_lbl.pack(fill="x", pady=(0, 14))

        ctk.CTkButton(scroll, text="Fechar", command=modal.destroy).pack(pady=10)

    # =========================================================================
    # ABA 3: CONFIGURAÇÕES
    # =========================================================================
    def _build_config_tab(self) -> None:
        """Constrói o painel de configurações de credenciais, provedor e limpeza da base."""
        self.tab_config = ctk.CTkScrollableFrame(self.main_container, corner_radius=10)

        ctk.CTkLabel(
            self.tab_config,
            text="Configurações do Sistema",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=16, pady=(16, 12))

        # Provedor e Chave de API
        ai_card = ctk.CTkFrame(self.tab_config, corner_radius=10)
        ai_card.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            ai_card,
            text="Provedor de Inteligência Artificial",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=14, pady=(12, 6))

        p_row = ctk.CTkFrame(ai_card, fg_color="transparent")
        p_row.pack(fill="x", padx=14, pady=4)

        ctk.CTkLabel(p_row, text="Provedor:").pack(side="left")
        self.cfg_prov_var = ctk.StringVar(value="Google Gemini")
        self.combo_prov = ctk.CTkOptionMenu(
            p_row,
            values=["Google Gemini", "OpenAI"],
            variable=self.cfg_prov_var,
            command=self._on_provider_change
        )
        self.combo_prov.pack(side="left", padx=10)

        ctk.CTkLabel(p_row, text="Modelo:").pack(side="left")
        self.cfg_model_var = ctk.StringVar(value="gemini-2.5-flash")
        self.combo_model = ctk.CTkComboBox(
            p_row,
            values=["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
            variable=self.cfg_model_var
        )
        self.combo_model.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(ai_card, text="Chave de API:").pack(anchor="w", padx=14, pady=(8, 2))

        key_row = ctk.CTkFrame(ai_card, fg_color="transparent")
        key_row.pack(fill="x", padx=14, pady=(0, 12))

        self.entry_key = ctk.CTkEntry(key_row, placeholder_text="Cole sua chave de API aqui...", show="*")
        self.entry_key.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_eye = ctk.CTkButton(key_row, text="👁", width=36, command=self._toggle_eye)
        self.btn_eye.pack(side="left")

        btn_save_ai = ctk.CTkButton(
            ai_card,
            text="Salvar Credenciais de IA",
            command=self._save_ai_settings,
            fg_color="#0D9488",
            hover_color="#0F766E"
        )
        btn_save_ai.pack(fill="x", padx=14, pady=(0, 14))

        # Manutenção da Base do Cérebro
        maint_card = ctk.CTkFrame(self.tab_config, corner_radius=10)
        maint_card.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            maint_card,
            text="Manutenção do Cérebro Local",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=14, pady=(12, 6))

        ctk.CTkLabel(
            maint_card,
            text="Localização dos Dados: ./Cerebro_Dados/ (JSON e Pastas de Imagens Categorizadas)",
            font=ctk.CTkFont(size=12),
            text_color="#64748B"
        ).pack(anchor="w", padx=14, pady=2)

        btn_clear = ctk.CTkButton(
            maint_card,
            text="🗑️ Limpar Base do Cérebro e Recortes de Imagem",
            command=self._clear_cerebro_database,
            fg_color="#DC2626",
            hover_color="#B91C1C"
        )
        btn_clear.pack(fill="x", padx=14, pady=(8, 14))

    # =========================================================================
    # ATUALIZAÇÃO DO MONITOR DO CÉREBRO EM TEMPO REAL (LIVE CALLBACK)
    # =========================================================================
    def update_live_cerebro_card(self, item: CerebroItem) -> None:
        """Chamado instantaneamente pela worker thread quando uma nova questão é resolvida."""
        def apply():
            # Atualiza badge de categoria
            self.badge_categoria.configure(text=f"[ {item.categoria.upper()} ]")

            # Atualiza contador no topo
            total = len(self.cerebro_manager.itens)
            self.lbl_total_cerebro.configure(text=f"Total na Memória: {total}")

            # Atualiza textos de pergunta, resposta e contexto
            self.txt_live_contexto.delete("1.0", "end")
            self.txt_live_contexto.insert("1.0", item.contexto_explicativo or "Sem descrição visual necessária.")

            self.txt_live_pergunta.delete("1.0", "end")
            self.txt_live_pergunta.insert("1.0", item.pergunta)

            self.lbl_live_resposta.configure(text=item.resposta_correta)

            # Atualiza a imagem renderizada na hora
            img_path = item.caminho_thumbnail or item.caminho_imagem
            if img_path and os.path.exists(img_path):
                try:
                    pil_img = Image.open(img_path)
                    ctk_img = ctk.CTkImage(
                        light_image=pil_img,
                        dark_image=pil_img,
                        size=(300, 180)
                    )
                    self.lbl_live_image.configure(image=ctk_img, text="")
                except Exception:
                    pass

        self.after(0, apply)

    # =========================================================================
    # MÉTODOS DE CONTROLE, THEME TOGGLE E SUPORTE
    # =========================================================================
    def _on_theme_toggle(self) -> None:
        """Alterna instantaneamente entre Modo Claro (Clean White) e Modo Escuro."""
        mode = self.current_theme.get()
        ctk.set_appearance_mode(mode)
        self.config_manager.set("theme_mode", mode)
        self.enqueue_log(f"Tema alterado para: {mode.upper()}", "INFO")

    def _on_provider_change(self, choice: str) -> None:
        if choice == "Google Gemini":
            models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
            self.combo_model.configure(values=models)
            self.cfg_model_var.set("gemini-2.5-flash")
        else:
            models = ["gpt-4o-mini", "gpt-4o"]
            self.combo_model.configure(values=models)
            self.cfg_model_var.set("gpt-4o-mini")

    def _toggle_eye(self) -> None:
        if self.entry_key.cget("show") == "*":
            self.entry_key.configure(show="")
            self.btn_eye.configure(text="🔒")
        else:
            self.entry_key.configure(show="*")
            self.btn_eye.configure(text="👁")

    def _save_ai_settings(self) -> None:
        prov = "gemini" if self.cfg_prov_var.get() == "Google Gemini" else "openai"
        key = self.entry_key.get().strip()
        model = self.cfg_model_var.get().strip()

        self.config_manager.set("api_provider", prov, auto_save=False)
        self.config_manager.set("api_key", key, auto_save=False)
        self.config_manager.set("model_name", model, auto_save=True)

        self.ai_service.update_credentials(prov, key, model)
        self.enqueue_log("Configurações de IA salvas com sucesso.", "SUCCESS")

    def _on_delay_change(self, val: float) -> None:
        rounded = round(val, 1)
        self.lbl_delay_val.configure(text=f"{rounded:.1f}s")
        self.config_manager.set("action_delay", rounded)

    def _clear_cerebro_database(self) -> None:
        self.cerebro_manager.clear_cerebro()
        self.lbl_total_cerebro.configure(text="Total na Memória: 0")
        self._refresh_cerebro_gallery()
        self.enqueue_log("Base do Cérebro e recortes foram limpos.", "WARNING")

    def _start_area_selection(self) -> None:
        self.withdraw()
        self.after(250, lambda: ScreenAreaSelector(self, self._on_area_selected))

    def _on_area_selected(self, x: int, y: int, w: int, h: int) -> None:
        self.deiconify()
        self.config_manager.update_quiz_region(x, y, w, h)
        self.lbl_area_status.configure(
            text=f"Área: X={x} Y={y} ({w}x{h} px)",
            text_color="#10B981"
        )
        self.enqueue_log(f"Área calibrada: [{x}, {y}, {w}, {h}].", "SUCCESS")

    def _start_next_button_selection(self) -> None:
        self.withdraw()
        self.after(250, lambda: PointSelector(self, self._on_next_selected, "Clique no Botão Próximo"))

    def _on_next_selected(self, x: int, y: int) -> None:
        self.deiconify()
        self.config_manager.update_next_button(x, y)
        self.lbl_next_status.configure(
            text=f"Botão Próximo: X={x} Y={y}",
            text_color="#10B981"
        )
        self.enqueue_log(f"Botão Próximo mapeado: ({x}, {y}).", "SUCCESS")

    def _cmd_start(self) -> None:
        self.engine.start()

    def _cmd_stop(self) -> None:
        self.engine.stop()

    def _setup_hotkeys(self) -> None:
        self.bind("<F8>", lambda e: self.engine.toggle_play_pause())
        self.bind("<Escape>", lambda e: self.engine.stop())

        try:
            import keyboard
            keyboard.add_hotkey("f8", lambda: self.after(0, self.engine.toggle_play_pause))
            keyboard.add_hotkey("esc", lambda: self.after(0, self.engine.stop))
        except Exception:
            pass

    def _load_saved_settings(self) -> None:
        cfg = self.config_manager.config_data

        # Tema salvo (padrão Light)
        saved_theme = cfg.get("theme_mode", "Light")
        self.current_theme.set(saved_theme)
        ctk.set_appearance_mode(saved_theme)

        # Provedor e modelo
        prov = "Google Gemini" if cfg.get("api_provider") == "gemini" else "OpenAI"
        self.cfg_prov_var.set(prov)
        self._on_provider_change(prov)
        self.cfg_model_var.set(cfg.get("model_name", "gemini-2.5-flash"))

        # API Key
        key = cfg.get("api_key", "")
        if key:
            self.entry_key.insert(0, key)

        # Região do quiz
        reg = cfg.get("quiz_region", {})
        if reg.get("configured", False):
            self.lbl_area_status.configure(
                text=f"Área: X={reg['x']} Y={reg['y']} ({reg['width']}x{reg['height']} px)",
                text_color="#10B981"
            )

        # Botão próximo
        nxt = cfg.get("next_button", {})
        if nxt.get("configured", False):
            self.lbl_next_status.configure(
                text=f"Botão Próximo: X={nxt['x']} Y={nxt['y']}",
                text_color="#10B981"
            )

        # Delay
        delay = float(cfg.get("action_delay", 2.5))
        self.slider_delay.set(delay)
        self.lbl_delay_val.configure(text=f"{delay:.1f}s")

        # Total do Cérebro
        total = len(self.cerebro_manager.itens)
        self.lbl_total_cerebro.configure(text=f"Total na Memória: {total}")

    def update_status_badge(self, state: str) -> None:
        def apply():
            if state == "EXECUTANDO":
                self.status_badge.configure(
                    text="● EXECUTANDO",
                    text_color="#16A34A",
                    fg_color=("#DCFCE7", "#14532D")
                )
            elif state == "ESCANEANDO":
                self.status_badge.configure(
                    text="● ESCANEANDO TELA",
                    text_color="#0284C7",
                    fg_color=("#E0F2FE", "#0C4A6E")
                )
            elif state == "ANALISANDO":
                self.status_badge.configure(
                    text="● ANALISANDO COM IA",
                    text_color="#7C3AED",
                    fg_color=("#EDE9FE", "#4C1D95")
                )
            elif state == "CLICANDO":
                self.status_badge.configure(
                    text="● CLICANDO RESPOSTA",
                    text_color="#D97706",
                    fg_color=("#FEF3C7", "#78350F")
                )
            elif state == "PAUSADO":
                self.status_badge.configure(
                    text="● PAUSADO",
                    text_color="#EAB308",
                    fg_color=("#FEF9C3", "#713F12")
                )
            else:
                self.status_badge.configure(
                    text="● PARADO",
                    text_color="#EF4444",
                    fg_color=("#FEE2E2", "#3B1E1E")
                )
        self.after(0, apply)

    def enqueue_log(self, message: str, level: str = "INFO") -> None:
        def apply():
            now = datetime.datetime.now().strftime("%H:%M:%S")
            prefix = {
                "INFO": "ℹ️ [INFO]",
                "SUCCESS": "✅ [OK]",
                "WARNING": "⚠️ [AVISO]",
                "ERROR": "❌ [ERRO]"
            }.get(level, "[LOG]")

            self.log_textbox.insert("end", f"[{now}] {prefix} {message}\n")
            self.log_textbox.see("end")
        self.after(0, apply)

    def _on_close(self) -> None:
        self.engine.stop()
        self.destroy()
