"""
Interface Gráfica Moderna (GUI) - Mastering Study Quiz
Painel vertical dockable para Windows (estilo EasyQuiz v3.9.0)
Suporta 2 temas estritos: Branco Clean (padrão) e Preto Mega Black.
Menu lateral com 5 abas: Resolver, Cérebro da IA, Métricas, Terminal e Configurações.
"""

import os
import sys
import time
import datetime
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional, Dict, Any, List
from PIL import Image
import customtkinter as ctk

from config_manager import ConfigManager
from ai_vision import AIVisionService
from cerebro_manager import CerebroManager, QuestionSessionRecord
from metrics_tracker import MetricsTracker
from automation import AutomationEngine
from overlay import ScreenAreaSelector, PointSelector

# Configuração Padrão Inicial: Tema Branco Clean
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class MasteringStudyQuizGUI(ctk.CTk):
    """Janela principal dockable do Mastering Study Quiz."""

    VERSION = "v3.9.0"

    def __init__(
        self,
        config_manager: ConfigManager,
        ai_service: AIVisionService,
        cerebro_manager: CerebroManager,
        metrics_tracker: MetricsTracker
    ):
        super().__init__()

        self.config_manager = config_manager
        self.ai_service = ai_service
        self.cerebro_manager = cerebro_manager
        self.metrics_tracker = metrics_tracker

        # Motor de automação RPA
        self.engine = AutomationEngine(
            config_manager=self.config_manager,
            ai_service=self.ai_service,
            cerebro_manager=self.cerebro_manager,
            metrics_tracker=self.metrics_tracker,
            log_callback=self.enqueue_log,
            status_callback=self.update_status_badge,
            live_cerebro_callback=self.on_live_cerebro_update,
            metrics_update_callback=self.on_metrics_update
        )

        # Configurações de Janela Vertical / Dockable
        self.title(f"Mastering Study Quiz {self.VERSION}")
        self.geometry("490x830")
        self.minsize(450, 720)

        # Configuração de Always on Top (padrão ativado para app lateral)
        is_top = self.config_manager.get("always_on_top", True)
        self.attributes("-topmost", is_top)

        # Configuração do Grid Mestre: Sidebar (esq) + Conteúdo Principal (dir)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Estado da Interface
        self.current_tab = "resolver"
        self.current_theme_str = self.config_manager.get("theme_mode", "Light")
        self.cached_images: Dict[str, ctk.CTkImage] = {}
        self.current_inspector_content: str = ""
        self.current_inspector_image_path: Optional[str] = None

        # Construção da Estrutura Visual
        self._build_sidebar()
        self._build_content_area()
        self._setup_hotkeys()
        self._apply_theme_colors()

        # Inicia loop do cronômetro da GUI (atualiza a cada 50ms)
        self._tick_stopwatch()

        # Protocolo de Encerramento Seguro
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =========================================================================
    # SIDEBAR LATERAL COM 5 ÍCONES
    # =========================================================================
    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(self, width=64, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)

        # Ícone 1: ✨ Resolver
        self.btn_nav_resolver = ctk.CTkButton(
            self.sidebar,
            text="✨",
            width=48,
            height=48,
            corner_radius=12,
            font=ctk.CTkFont(size=20),
            command=lambda: self._switch_tab("resolver")
        )
        self.btn_nav_resolver.grid(row=0, column=0, padx=8, pady=(16, 6))

        # Ícone 2: 🎯 Cérebro da IA
        self.btn_nav_cerebro = ctk.CTkButton(
            self.sidebar,
            text="🎯",
            width=48,
            height=48,
            corner_radius=12,
            font=ctk.CTkFont(size=18),
            command=lambda: self._switch_tab("cerebro")
        )
        self.btn_nav_cerebro.grid(row=1, column=0, padx=8, pady=6)

        # Ícone 3: 🕒 Métricas
        self.btn_nav_metricas = ctk.CTkButton(
            self.sidebar,
            text="🕒",
            width=48,
            height=48,
            corner_radius=12,
            font=ctk.CTkFont(size=18),
            command=lambda: self._switch_tab("metricas")
        )
        self.btn_nav_metricas.grid(row=2, column=0, padx=8, pady=6)

        # Ícone 4: <> Terminal
        self.btn_nav_terminal = ctk.CTkButton(
            self.sidebar,
            text="< >",
            width=48,
            height=48,
            corner_radius=12,
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            command=lambda: self._switch_tab("terminal")
        )
        self.btn_nav_terminal.grid(row=3, column=0, padx=8, pady=6)

        # Ícone 5: ⚙️ Configurações (Rodapé)
        self.btn_nav_config = ctk.CTkButton(
            self.sidebar,
            text="⚙️",
            width=48,
            height=48,
            corner_radius=12,
            font=ctk.CTkFont(size=18),
            command=lambda: self._switch_tab("config")
        )
        self.btn_nav_config.grid(row=5, column=0, padx=8, pady=16)

    # =========================================================================
    # ÁREA PRINCIPAL DINÂMICA
    # =========================================================================
    def _build_content_area(self) -> None:
        self.content_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        self._build_tela_resolver()
        self._build_tela_cerebro()
        self._build_tela_metricas()
        self._build_tela_terminal()
        self._build_tela_config()

        self._switch_tab("resolver")

    def _switch_tab(self, tab_id: str) -> None:
        self.tab_resolver.grid_remove()
        self.tab_cerebro.grid_remove()
        self.tab_metricas.grid_remove()
        self.tab_terminal.grid_remove()
        self.tab_config.grid_remove()

        inactive_bg = "transparent"
        active_bg = ("#2563EB", "#3B82F6")
        text_white = "#FFFFFF"

        for btn in (self.btn_nav_resolver, self.btn_nav_cerebro, self.btn_nav_metricas, self.btn_nav_terminal, self.btn_nav_config):
            btn.configure(fg_color=inactive_bg, text_color=("black", "white"))

        self.current_tab = tab_id
        if tab_id == "resolver":
            self.tab_resolver.grid(row=0, column=0, sticky="nsew")
            self.btn_nav_resolver.configure(fg_color=active_bg, text_color=text_white)
        elif tab_id == "cerebro":
            self.tab_cerebro.grid(row=0, column=0, sticky="nsew")
            self.btn_nav_cerebro.configure(fg_color=active_bg, text_color=text_white)
            self._reload_cerebro_tree()
        elif tab_id == "metricas":
            self.tab_metricas.grid(row=0, column=0, sticky="nsew")
            self.btn_nav_metricas.configure(fg_color=active_bg, text_color=text_white)
            self._refresh_metricas_ui()
        elif tab_id == "terminal":
            self.tab_terminal.grid(row=0, column=0, sticky="nsew")
            self.btn_nav_terminal.configure(fg_color=active_bg, text_color=text_white)
        elif tab_id == "config":
            self.tab_config.grid(row=0, column=0, sticky="nsew")
            self.btn_nav_config.configure(fg_color=active_bg, text_color=text_white)

    # =========================================================================
    # TELA 1: RESOLVER (AUTOPILOT & OPERAÇÕES)
    # =========================================================================
    def _build_tela_resolver(self) -> None:
        self.tab_resolver = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.tab_resolver.grid_columnconfigure(0, weight=1)
        self.tab_resolver.grid_rowconfigure(2, weight=1)

        # Header: Título, Versão e Status Badge
        header_card = ctk.CTkFrame(self.tab_resolver, corner_radius=12)
        header_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        title_box = ctk.CTkFrame(header_card, fg_color="transparent")
        title_box.pack(side="left", padx=14, pady=12)

        lbl_title = ctk.CTkLabel(
            title_box,
            text=f"Mastering Study Quiz",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold")
        )
        lbl_title.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            title_box,
            text=f"{self.VERSION}  |  Autopilot Desktop",
            font=ctk.CTkFont(size=11),
            text_color="#64748B"
        )
        lbl_sub.pack(anchor="w")

        self.status_pill = ctk.CTkLabel(
            header_card,
            text="PRONTO",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#16A34A",
            fg_color=("#DCFCE7", "#14532D"),
            corner_radius=8,
            padx=12,
            pady=6
        )
        self.status_pill.pack(side="right", padx=14, pady=12)

        # Bloco Principal Hero: Botão RESOLVER AUTOPILOT + Menu ⋮
        hero_box = ctk.CTkFrame(self.tab_resolver, corner_radius=12)
        hero_box.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        hero_row = ctk.CTkFrame(hero_box, fg_color="transparent")
        hero_row.pack(fill="x", padx=14, pady=16)

        self.btn_autopilot = ctk.CTkButton(
            hero_row,
            text="✨ RESOLVER AUTOPILOT",
            height=52,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            corner_radius=10,
            command=self._cmd_toggle_autopilot
        )
        self.btn_autopilot.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_menu_dots = ctk.CTkButton(
            hero_row,
            text="⋮",
            width=42,
            height=52,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("black", "white"),
            hover_color=("#CBD5E1", "#475569"),
            corner_radius=10,
            command=self._open_quick_calibration_menu
        )
        self.btn_menu_dots.pack(side="right")

        # Barra de Status Dinâmica em Tempo Real
        self.lbl_status_bar = ctk.CTkLabel(
            hero_box,
            text="Sistema aguardando. Pressione F8 ou clique em Resolver.",
            font=ctk.CTkFont(size=12),
            text_color="#64748B"
        )
        self.lbl_status_bar.pack(anchor="w", padx=16, pady=(0, 12))

        # Painel Central de Visualização Rápida no Resolver
        resolver_body = ctk.CTkScrollableFrame(self.tab_resolver, corner_radius=12)
        resolver_body.grid(row=2, column=0, sticky="nsew", pady=(0, 10))

        # Status das Calibrações
        calib_info_box = ctk.CTkFrame(resolver_body, corner_radius=8)
        calib_info_box.pack(fill="x", padx=4, pady=4)

        self.lbl_res_area = ctk.CTkLabel(
            calib_info_box,
            text="Área do Quiz: Não calibrada",
            font=ctk.CTkFont(size=12),
            text_color="#F59E0B"
        )
        self.lbl_res_area.pack(anchor="w", padx=12, pady=(8, 2))

        self.lbl_res_next = ctk.CTkLabel(
            calib_info_box,
            text="Botão Próximo: Não mapeado",
            font=ctk.CTkFont(size=12),
            text_color="#64748B"
        )
        self.lbl_res_next.pack(anchor="w", padx=12, pady=(2, 8))

        # Card de Última Questão Resolvida
        ctk.CTkLabel(
            resolver_body,
            text="Última Resposta Identificada:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=4, pady=(8, 2))

        self.txt_res_last_answer = ctk.CTkTextbox(resolver_body, height=130, wrap="word", corner_radius=8)
        self.txt_res_last_answer.pack(fill="x", padx=4, pady=(0, 6))
        self.txt_res_last_answer.insert("1.0", "Nenhuma questão processada ainda nesta sessão.")

        # Rodapé Informativo
        footer = ctk.CTkFrame(self.tab_resolver, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew")

        ctk.CTkLabel(
            footer,
            text="Motor Híbrido (RAG + Visão + Automação)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94A3B8"
        ).pack(side="left", padx=4)

        self.switch_topmost = ctk.CTkSwitch(
            footer,
            text="Always on Top",
            font=ctk.CTkFont(size=11),
            command=self._on_toggle_topmost
        )
        self.switch_topmost.pack(side="right")
        if self.config_manager.get("always_on_top", True):
            self.switch_topmost.select()

    def _open_quick_calibration_menu(self) -> None:
        """Abre modal com opções de calibração rápida ao clicar nos três pontos (⋮)."""
        modal = ctk.CTkToplevel(self)
        modal.title("Calibração da Tela")
        modal.geometry("340x260")
        modal.attributes("-topmost", True)

        ctk.CTkLabel(modal, text="Menu de Calibração Rápida", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(16, 10))

        ctk.CTkButton(
            modal,
            text="🔍 Delimitar Área do Quiz",
            height=38,
            command=lambda: [modal.destroy(), self._start_area_selection()]
        ).pack(fill="x", padx=20, pady=6)

        ctk.CTkButton(
            modal,
            text="🎯 Mapear Botão Próximo",
            height=38,
            command=lambda: [modal.destroy(), self._start_next_button_selection()]
        ).pack(fill="x", padx=20, pady=6)

        ctk.CTkButton(
            modal,
            text="Fechar",
            height=32,
            fg_color="#64748B",
            command=modal.destroy
        ).pack(fill="x", padx=20, pady=(12, 0))

    # =========================================================================
    # TELA 2: CÉREBRO DA IA (VISUALIZAÇÃO AO VIVO + EXPLORADOR DE ÁRVORE)
    # =========================================================================
    def _build_tela_cerebro(self) -> None:
        self.tab_cerebro = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.tab_cerebro.grid_columnconfigure(0, weight=1)
        self.tab_cerebro.grid_rowconfigure(0, weight=4)  # Painel Superior (Inspetor)
        self.tab_cerebro.grid_rowconfigure(1, weight=6)  # Painel Inferior (Árvore)

        # 1. PAINEL SUPERIOR: Inspetor Visual em Tempo Real
        inspector_frame = ctk.CTkFrame(self.tab_cerebro, corner_radius=12)
        inspector_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        inspector_frame.grid_columnconfigure(0, weight=1)
        inspector_frame.grid_rowconfigure(1, weight=1)

        # Header do Inspetor
        insp_hdr = ctk.CTkFrame(inspector_frame, fg_color="transparent")
        insp_hdr.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))

        self.lbl_insp_badge = ctk.CTkLabel(
            insp_hdr,
            text="[ CÉREBRO EM TEMPO REAL ]",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#2563EB",
            fg_color=("#DBEAFE", "#1E3A8A"),
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.lbl_insp_badge.pack(side="left")

        btn_copy = ctk.CTkButton(
            insp_hdr,
            text="Copiar",
            width=55,
            height=26,
            font=ctk.CTkFont(size=11),
            command=self._cmd_copy_inspector
        )
        btn_copy.pack(side="right", padx=(4, 0))

        btn_expand = ctk.CTkButton(
            insp_hdr,
            text="🔍 Zoom",
            width=60,
            height=26,
            font=ctk.CTkFont(size=11),
            command=self._cmd_expand_inspector_image
        )
        btn_expand.pack(side="right")

        # Conteúdo do Inspetor (Suporta Imagem ou Texto)
        self.insp_content_box = ctk.CTkScrollableFrame(inspector_frame, corner_radius=8, fg_color=("white", "#18181b"))
        self.insp_content_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))

        self.lbl_insp_image = ctk.CTkLabel(
            self.insp_content_box,
            text="A imagem capturada ou o arquivo clicado abaixo aparecerá aqui."
        )
        self.lbl_insp_image.pack(pady=4)

        self.txt_insp_description = ctk.CTkLabel(
            self.insp_content_box,
            text="",
            font=ctk.CTkFont(size=11),
            wraplength=410,
            justify="left"
        )
        self.txt_insp_description.pack(pady=4)

        # 2. PAINEL INFERIOR: Explorador de Árvore "Contexto Global"
        tree_frame = ctk.CTkFrame(self.tab_cerebro, corner_radius=12)
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(1, weight=1)

        tree_header = ctk.CTkFrame(tree_frame, fg_color="transparent")
        tree_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            tree_header,
            text="📁 Explorador de Contexto Global (Cerebro_Dados)",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left")

        btn_refresh_tree = ctk.CTkButton(
            tree_header,
            text="↻",
            width=28,
            height=24,
            command=self._reload_cerebro_tree
        )
        btn_refresh_tree.pack(side="right")

        self.tree_scroll = ctk.CTkScrollableFrame(tree_frame, fg_color="transparent")
        self.tree_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 10))

    def _reload_cerebro_tree(self) -> None:
        """Reconstrói a árvore de arquivos físicos e mídias salvos em Cerebro_Dados."""
        for w in self.tree_scroll.winfo_children():
            w.destroy()

        files_map = self.cerebro_manager.get_latest_session_files()

        # Seção 1: 📁 Resposta da IA
        self._add_tree_category("📁 Resposta da IA")
        self._add_tree_file_node("rationale.md", files_map.get("rationale", ""), "Explicação passo a passo")
        self._add_tree_file_node("actions.json", files_map.get("actions", ""), "Coordenadas e ação executada")
        self._add_tree_file_node("resumo.txt", files_map.get("resumo", ""), "Enunciado e resposta curta")

        # Seção 2: 📁 Contexto & Prompt
        self._add_tree_category("📁 Contexto & Prompt")
        self._add_tree_file_node("prompt-enviado.txt", files_map.get("prompt", ""), "Prompt exato da IA")
        self._add_tree_file_node("rag-context.txt", files_map.get("rag", ""), "Contexto recuperado da memória")

        # Seção 3: 📁 Metadados
        self._add_tree_category("📁 Metadados")
        self._add_tree_file_node("modelo.info", files_map.get("modelo", ""), "Modelo de LLM utilizado")
        self._add_tree_file_node("latencia.info", files_map.get("latencia", ""), "Tempo de resposta em ms")
        self._add_tree_file_node("tokens.info", files_map.get("tokens", ""), "Tokens consumidos")

        # Seção 4: 📁 Mídia (Imagens Contextualizadas)
        self._add_tree_category("📁 Mídia (Imagens Contextualizadas)")
        media_items = self.cerebro_manager.list_all_media_items()
        if not media_items:
            ctk.CTkLabel(
                self.tree_scroll,
                text="   (Nenhuma mídia capturada ainda)",
                font=ctk.CTkFont(size=11),
                text_color="#94A3B8"
            ).pack(anchor="w")
        else:
            for m in media_items:
                self._add_tree_media_node(m)

    def _add_tree_category(self, title: str) -> None:
        ctk.CTkLabel(
            self.tree_scroll,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2563EB"
        ).pack(anchor="w", padx=4, pady=(8, 2))

    def _add_tree_file_node(self, filename: str, filepath: str, description: str) -> None:
        btn = ctk.CTkButton(
            self.tree_scroll,
            text=f"   📄 {filename}  -  {description}",
            anchor="w",
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            text_color=("black", "white"),
            hover_color=("#E2E8F0", "#334155"),
            command=lambda p=filepath, n=filename: self._display_file_in_inspector(n, p)
        )
        btn.pack(fill="x", padx=6, pady=1)

    def _add_tree_media_node(self, media_item: Dict[str, str]) -> None:
        btn = ctk.CTkButton(
            self.tree_scroll,
            text=f"   🖼️ {media_item['label']}",
            anchor="w",
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            text_color=("black", "white"),
            hover_color=("#E2E8F0", "#334155"),
            command=lambda p=media_item["path"], l=media_item["label"]: self._display_media_in_inspector(l, p)
        )
        btn.pack(fill="x", padx=6, pady=1)

    def _display_file_in_inspector(self, name: str, filepath: str) -> None:
        content = self.cerebro_manager.read_file_safe(filepath)
        self.current_inspector_content = content
        self.current_inspector_image_path = None

        self.lbl_insp_badge.configure(text=f"[ ARQUIVO: {name} ]")
        self.lbl_insp_image.configure(image=None, text="")
        self.txt_insp_description.configure(text=content)

    def _display_media_in_inspector(self, label: str, img_path: str) -> None:
        self.current_inspector_image_path = img_path
        self.current_inspector_content = label
        self.lbl_insp_badge.configure(text="[ MÍDIA CONTEXTUALIZADA ]")
        self.txt_insp_description.configure(text=label)

        if os.path.exists(img_path):
            try:
                pil_img = Image.open(img_path)
                w, h = pil_img.size
                scale = min(360 / max(1, w), 200 / max(1, h))
                dw = max(50, int(w * scale))
                dh = max(50, int(h * scale))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(dw, dh))
                self.lbl_insp_image.configure(image=ctk_img, text="")
            except Exception as e:
                self.lbl_insp_image.configure(image=None, text=f"Erro ao abrir imagem: {e}")

    def on_live_cerebro_update(self, record: QuestionSessionRecord) -> None:
        """Atualização instantânea do Cérebro em Tempo Real chamada pela worker thread."""
        def apply():
            badge_text = f"[ {record.categoria_imagem.upper()} ]" if record.possui_elemento_visual else "[ TEXTO PURO ]"
            self.lbl_insp_badge.configure(text=badge_text)

            desc = f"{record.contexto_imagem}\n\nEnunciado: {record.pergunta}\nResposta: {record.resposta_correta}"
            self.current_inspector_content = desc
            self.txt_insp_description.configure(text=desc)

            if record.caminho_imagem and os.path.exists(record.caminho_imagem):
                self.current_inspector_image_path = record.caminho_imagem
                try:
                    pil_img = Image.open(record.caminho_imagem)
                    w, h = pil_img.size
                    scale = min(360 / max(1, w), 200 / max(1, h))
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(int(w*scale), int(h*scale)))
                    self.lbl_insp_image.configure(image=ctk_img, text="")
                except Exception:
                    pass

            # Atualiza também o card da tela Resolver
            self.txt_res_last_answer.delete("1.0", "end")
            self.txt_res_last_answer.insert(
                "1.0",
                f"Questão #{record.id}: {record.pergunta[:80]}...\n\nResposta: {record.resposta_correta}\nConfiança: {record.confianca*100:.1f}%"
            )

            # Atualiza a árvore do explorador
            self._reload_cerebro_tree()

        self.after(0, apply)

    def _cmd_copy_inspector(self) -> None:
        if self.current_inspector_content:
            self.clipboard_clear()
            self.clipboard_append(self.current_inspector_content)
            self.enqueue_log("Conteúdo do inspetor copiado para a área de transferência.", "SUCCESS")

    def _cmd_expand_inspector_image(self) -> None:
        if not self.current_inspector_image_path or not os.path.exists(self.current_inspector_image_path):
            messagebox.showinfo("Inspetor", "Nenhuma imagem ativa para expandir.")
            return

        modal = ctk.CTkToplevel(self)
        modal.title("Inspeção de Mídia - Tela Cheia")
        modal.geometry("750x650")
        modal.attributes("-topmost", True)

        try:
            orig = Image.open(self.current_inspector_image_path)
            w, h = orig.size
            ratio = min(700 / max(1, w), 540 / max(1, h))
            full_ctk = ctk.CTkImage(light_image=orig, dark_image=orig, size=(int(w*ratio), int(h*ratio)))
            ctk.CTkLabel(modal, image=full_ctk, text="").pack(expand=True, fill="both", padx=10, pady=10)
        except Exception as e:
            ctk.CTkLabel(modal, text=f"Erro: {e}").pack()

    # =========================================================================
    # TELA 3: MÉTRICAS (CRONÔMETRO DIGITAL & HISTÓRICO)
    # =========================================================================
    def _build_tela_metricas(self) -> None:
        self.tab_metricas = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.tab_metricas.grid_columnconfigure(0, weight=1)
        self.tab_metricas.grid_rowconfigure(2, weight=1)

        # 1. Cronômetro Digital Grande para a Questão Atual
        stopwatch_box = ctk.CTkFrame(self.tab_metricas, corner_radius=12)
        stopwatch_box.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            stopwatch_box,
            text="QUESTÃO ATUAL",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#64748B"
        ).pack(pady=(12, 0))

        self.lbl_stopwatch = ctk.CTkLabel(
            stopwatch_box,
            text="00:00.00",
            font=ctk.CTkFont(family="Consolas", size=38, weight="bold"),
            text_color="#2563EB"
        )
        self.lbl_stopwatch.pack(pady=2)

        meta_row = ctk.CTkFrame(stopwatch_box, fg_color="transparent")
        meta_row.pack(fill="x", padx=16, pady=(0, 12))

        self.lbl_sw_status = ctk.CTkLabel(meta_row, text="Status: Em espera", font=ctk.CTkFont(size=12))
        self.lbl_sw_status.pack(side="left")

        self.lbl_sw_tokens = ctk.CTkLabel(meta_row, text="Tokens: 0", font=ctk.CTkFont(size=12))
        self.lbl_sw_tokens.pack(side="right")

        # 2. Cards de Resumo da Sessão
        cards_row = ctk.CTkFrame(self.tab_metricas, fg_color="transparent")
        cards_row.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        cards_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.card_total_time = self._create_metric_card(cards_row, 0, "TEMPO TOTAL", "00:00")
        self.card_avg_time = self._create_metric_card(cards_row, 1, "MÉDIA / Q.", "0.0s")
        self.card_count = self._create_metric_card(cards_row, 2, "RESPONDIDAS", "0")

        # 3. Histórico por Questão
        hist_frame = ctk.CTkFrame(self.tab_metricas, corner_radius=12)
        hist_frame.grid(row=2, column=0, sticky="nsew")
        hist_frame.grid_columnconfigure(0, weight=1)
        hist_frame.grid_rowconfigure(1, weight=1)

        hist_hdr = ctk.CTkFrame(hist_frame, fg_color="transparent")
        hist_hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            hist_hdr,
            text="Histórico da Sessão",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left")

        btn_copy_rep = ctk.CTkButton(
            hist_hdr,
            text="Copiar Relatório",
            width=110,
            height=26,
            font=ctk.CTkFont(size=11),
            command=self._cmd_copy_report
        )
        btn_copy_rep.pack(side="right", padx=(6, 0))

        btn_clear_hist = ctk.CTkButton(
            hist_hdr,
            text="🗑️",
            width=32,
            height=26,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            command=self._cmd_clear_history
        )
        btn_clear_hist.pack(side="right")

        self.hist_scroll = ctk.CTkScrollableFrame(hist_frame, fg_color="transparent")
        self.hist_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 10))

    def _create_metric_card(self, parent: ctk.CTkFrame, col: int, label: str, initial_val: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.grid(row=0, column=col, padx=3, sticky="ew")

        ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748B").pack(pady=(8, 2))
        val_lbl = ctk.CTkLabel(card, text=initial_val, font=ctk.CTkFont(size=17, weight="bold"))
        val_lbl.pack(pady=(0, 8))
        return val_lbl

    def _tick_stopwatch(self) -> None:
        """Loop de alta precisão do cronômetro da interface."""
        if self.engine.is_running:
            sec = self.metrics_tracker.get_current_question_elapsed()
            self.lbl_stopwatch.configure(text=self.metrics_tracker.format_stopwatch(sec))
            self.lbl_sw_status.configure(text="Status: Ativo")
        else:
            self.lbl_sw_status.configure(text="Status: Em espera")

        # Atualiza métricas agregadas da sessão
        total_sec = self.metrics_tracker.get_total_session_elapsed()
        self.card_total_time.configure(text=self.metrics_tracker.format_minutes_seconds(total_sec))
        self.card_avg_time.configure(text=f"{self.metrics_tracker.get_average_time():.1f}s")
        self.card_count.configure(text=str(len(self.metrics_tracker.questions_history)))

        self.after(60, self._tick_stopwatch)

    def on_metrics_update(self) -> None:
        def apply():
            self._refresh_metricas_ui()
        self.after(0, apply)

    def _refresh_metricas_ui(self) -> None:
        for w in self.hist_scroll.winfo_children():
            w.destroy()

        history = self.metrics_tracker.questions_history
        if not history:
            ctk.CTkLabel(self.hist_scroll, text="Nenhuma questão concluída nesta sessão.", font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(pady=20)
            return

        for q in reversed(history):
            row = ctk.CTkFrame(self.hist_scroll, corner_radius=8)
            row.pack(fill="x", padx=4, pady=3)

            visual_tag = f"[{q['categoria']}]" if q["possui_visual"] else "[Texto]"
            ctk.CTkLabel(row, text=f"#{q['numero']}  {visual_tag}", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=f"Resp: {q['resposta'][:22]}", font=ctk.CTkFont(size=11)).pack(side="left", padx=4)
            ctk.CTkLabel(row, text=f"{q['tempo_formatado']}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#2563EB").pack(side="right", padx=10)

    def _cmd_copy_report(self) -> None:
        rep = self.metrics_tracker.generate_report_markdown()
        self.clipboard_clear()
        self.clipboard_append(rep)
        self.enqueue_log("Relatório de sessão copiado para a área de transferência.", "SUCCESS")

    def _cmd_clear_history(self) -> None:
        self.metrics_tracker.clear()
        self._refresh_metricas_ui()
        self.enqueue_log("Histórico de métricas resetado.", "INFO")

    # =========================================================================
    # TELA 4: TERMINAL (COMANDOS & LOGS)
    # =========================================================================
    def _build_tela_terminal(self) -> None:
        self.tab_terminal = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.tab_terminal.grid_columnconfigure(0, weight=1)
        self.tab_terminal.grid_rowconfigure(1, weight=1)

        # Barra Superior: Segmented Button (Terminal vs Output) + Ações
        top_bar = ctk.CTkFrame(self.tab_terminal, corner_radius=10)
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.term_view_mode = ctk.StringVar(value="Terminal")
        seg = ctk.CTkSegmentedButton(
            top_bar,
            values=["Terminal", "Output"],
            variable=self.term_view_mode,
            command=self._on_term_mode_change
        )
        seg.pack(side="left", padx=10, pady=8)

        btn_copy_logs = ctk.CTkButton(top_bar, text="Copiar Logs", width=85, height=28, command=self._cmd_copy_terminal_logs)
        btn_copy_logs.pack(side="right", padx=(4, 10))

        btn_clear_logs = ctk.CTkButton(top_bar, text="Limpar", width=65, height=28, fg_color="#64748B", command=self._cmd_clear_terminal_logs)
        btn_clear_logs.pack(side="right")

        # Área de Visualização do Console
        term_box = ctk.CTkFrame(self.tab_terminal, corner_radius=12)
        term_box.grid(row=1, column=0, sticky="nsew")
        term_box.grid_columnconfigure(0, weight=1)
        term_box.grid_rowconfigure(0, weight=1)

        self.txt_terminal_output = ctk.CTkTextbox(
            term_box,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("white", "#09090b"),
            wrap="word"
        )
        self.txt_terminal_output.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Linha de Comando Interativa (Modo Terminal)
        self.cmd_input_row = ctk.CTkFrame(term_box, fg_color="transparent")
        self.cmd_input_row.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        ctk.CTkLabel(self.cmd_input_row, text=">", font=ctk.CTkFont(family="Consolas", size=14, weight="bold")).pack(side="left", padx=(0, 6))

        self.entry_command = ctk.CTkEntry(
            self.cmd_input_row,
            placeholder_text="Digite um comando (help, status, scan, brain, solve, stop)...",
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.entry_command.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_command.bind("<Return>", lambda e: self._execute_terminal_command())

        btn_exec = ctk.CTkButton(self.cmd_input_row, text="Executar", width=80, command=self._execute_terminal_command)
        btn_exec.pack(side="right")

    def _on_term_mode_change(self, mode: str) -> None:
        if mode == "Output":
            self.cmd_input_row.grid_remove()
        else:
            self.cmd_input_row.grid()

    def _execute_terminal_command(self) -> None:
        cmd = self.entry_command.get().strip()
        if not cmd:
            return
        self.entry_command.delete(0, "end")
        self.enqueue_log(f"> {cmd}", "INFO")

        parts = cmd.lower().split()
        op = parts[0]

        if op == "help":
            help_text = (
                "Comandos disponíveis:\n"
                "  help       - Exibe esta lista de instruções\n"
                "  status     - Exibe estado atual do Autopilot e calibrações\n"
                "  clear      - Limpa o terminal\n"
                "  solve      - Inicia o loop de resolução\n"
                "  stop       - Para a automação imediatamente\n"
                "  scan       - Executa uma única captura de teste\n"
                "  brain      - Mostra o total de registros salvos na pasta\n"
                "  dryrun on  - Ativa modo simulação (sem cliques)\n"
                "  dryrun off - Desativa modo simulação"
            )
            self.enqueue_log(help_text, "INFO")
        elif op == "status":
            reg = self.config_manager.get("quiz_region", {})
            st = "Executando" if self.engine.is_running else "Parado"
            self.enqueue_log(f"Status: {st} | Região Calibrada: {reg.get('configured', False)}", "SUCCESS")
        elif op == "clear":
            self.txt_terminal_output.delete("1.0", "end")
        elif op == "solve":
            self.engine.start()
        elif op == "stop":
            self.engine.stop()
        elif op == "brain":
            tot = len(self.cerebro_manager.database)
            self.enqueue_log(f"Base do Cérebro: {tot} sessões registradas em Cerebro_Dados.", "SUCCESS")
        elif op == "dryrun":
            if len(parts) > 1 and parts[1] == "on":
                self.config_manager.set("dry_run_mode", True)
                self.update_status_badge("SIMULAÇÃO DRY-RUN")
                self.enqueue_log("Modo Dry-Run ATIVADO.", "WARNING")
            else:
                self.config_manager.set("dry_run_mode", False)
                self.update_status_badge("PARADO")
                self.enqueue_log("Modo Dry-Run DESATIVADO.", "INFO")
        else:
            self.enqueue_log(f"Comando desconhecido: '{cmd}'. Digite 'help' para ajuda.", "WARNING")

    def _cmd_copy_terminal_logs(self) -> None:
        text = self.txt_terminal_output.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.enqueue_log("Logs copiados para a área de transferência.", "SUCCESS")

    def _cmd_clear_terminal_logs(self) -> None:
        self.txt_terminal_output.delete("1.0", "end")

    # =========================================================================
    # TELA 5: CONFIGURAÇÕES (5 SUB-ABAS)
    # =========================================================================
    def _build_tela_config(self) -> None:
        self.tab_config = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.tab_config.grid_columnconfigure(0, weight=1)
        self.tab_config.grid_rowconfigure(1, weight=1)

        # Tabview com as 5 Sub-abas Superiores
        self.config_tabview = ctk.CTkTabview(self.tab_config, corner_radius=12)
        self.config_tabview.grid(row=0, column=0, sticky="nsew")

        tab_geral = self.config_tabview.add("Geral")
        tab_tokens = self.config_tabview.add("Tokens")
        tab_visual = self.config_tabview.add("Visual")
        tab_ia = self.config_tabview.add("IA")
        tab_sistema = self.config_tabview.add("Sistema")

        self._populate_config_geral(tab_geral)
        self._populate_config_tokens(tab_tokens)
        self._populate_config_visual(tab_visual)
        self._populate_config_ia(tab_ia)
        self._populate_config_sistema(tab_sistema)

    def _populate_config_geral(self, tab: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(scroll, text="Comportamento da Automação", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(4, 6))

        self.sw_auto_apply = self._create_switch(scroll, "Auto Aplicar (Clica na resposta automaticamente)", "auto_apply")
        self.sw_auto_advance = self._create_switch(scroll, "Auto Avançar (Clica no botão Próximo)", "auto_advance")
        self.sw_dry_run = self._create_switch(scroll, "Modo Dry-Run (Simulação sem cliques reais)", "dry_run_mode", callback=self._on_dry_run_switch)
        self.sw_dark_host = self._create_switch(scroll, "Dark Mode no Site Host", "dark_mode_host")
        self.sw_stacked_notifs = self._create_switch(scroll, "Notificações Empilhadas", "stacked_notifications")
        self.sw_show_tokens = self._create_switch(scroll, "Exibir Uso de Tokens", "show_token_usage")
        self.sw_sound = self._create_switch(scroll, "Feedback Sonoro (Bip na resposta)", "sound_feedback")
        self.sw_compact = self._create_switch(scroll, "Modo Compacto", "compact_mode")

    def _create_switch(self, parent: ctk.CTkFrame, text: str, config_key: str, callback=None) -> ctk.CTkSwitch:
        sw = ctk.CTkSwitch(
            parent,
            text=text,
            font=ctk.CTkFont(size=12),
            command=lambda: [self.config_manager.set(config_key, bool(sw.get())), callback() if callback else None]
        )
        sw.pack(anchor="w", pady=6)
        if self.config_manager.get(config_key, False):
            sw.select()
        return sw

    def _on_dry_run_switch(self) -> None:
        if self.config_manager.get("dry_run_mode", False):
            self.update_status_badge("SIMULAÇÃO DRY-RUN")
        else:
            self.update_status_badge("PARADO")

    def _populate_config_tokens(self, tab: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        header_row = ctk.CTkFrame(scroll, fg_color="transparent")
        header_row.pack(fill="x", pady=(4, 6))

        ctk.CTkLabel(header_row, text="Gerenciador de Chaves de API (Gemini)", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        btn_get_key = ctk.CTkButton(
            header_row,
            text="+ OBTER CHAVE ↗",
            width=130,
            height=26,
            fg_color="#0D9488",
            hover_color="#0F766E",
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey")
        )
        btn_get_key.pack(side="right")

        # Campo para Adicionar Nova Chave
        add_row = ctk.CTkFrame(scroll, fg_color="transparent")
        add_row.pack(fill="x", pady=(4, 10))

        self.entry_new_key = ctk.CTkEntry(add_row, placeholder_text="Cole sua chave AIzaSy... aqui", show="*")
        self.entry_new_key.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_add_k = ctk.CTkButton(add_row, text="+", width=36, font=ctk.CTkFont(size=16, weight="bold"), command=self._cmd_add_key)
        btn_add_k.pack(side="right")

        ctk.CTkLabel(scroll, text="Chaves Ativas e Rotação Automática:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(8, 4))

        self.keys_list_container = ctk.CTkFrame(scroll, fg_color="transparent")
        self.keys_list_container.pack(fill="x")
        self._refresh_keys_list()

    def _refresh_keys_list(self) -> None:
        for w in self.keys_list_container.winfo_children():
            w.destroy()

        keys = self.config_manager.get("api_keys", [])
        if not keys:
            ctk.CTkLabel(self.keys_list_container, text="Nenhuma chave adicionada ainda.", font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(anchor="w", pady=4)
            return

        for k in keys:
            row = ctk.CTkFrame(self.keys_list_container, corner_radius=6)
            row.pack(fill="x", pady=2)

            masked = k[:8] + "..." + k[-4:] if len(k) > 12 else k
            ctk.CTkLabel(row, text=f"🔑 {masked}", font=ctk.CTkFont(family="Consolas", size=11)).pack(side="left", padx=10, pady=6)

            btn_del = ctk.CTkButton(
                row,
                text="✕",
                width=28,
                height=22,
                fg_color="#DC2626",
                hover_color="#B91C1C",
                command=lambda key_to_del=k: self._cmd_remove_key(key_to_del)
            )
            btn_del.pack(side="right", padx=6, pady=4)

    def _cmd_add_key(self) -> None:
        k = self.entry_new_key.get().strip()
        if k:
            self.config_manager.add_api_key(k)
            self.entry_new_key.delete(0, "end")
            self._refresh_keys_list()
            self.enqueue_log("Chave de API adicionada ao gerenciador de rotação.", "SUCCESS")

    def _cmd_remove_key(self, k: str) -> None:
        self.config_manager.remove_api_key(k)
        self._refresh_keys_list()
        self.enqueue_log("Chave de API removida.", "INFO")

    def _populate_config_visual(self, tab: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(scroll, text="Aparência do Painel (2 Temas Estritos)", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(4, 6))

        # Seletor Exclusivo de 2 Temas
        self.theme_selector = ctk.CTkSegmentedButton(
            scroll,
            values=["Branco (Light)", "Preto (Dark)"],
            command=self._on_theme_select
        )
        self.theme_selector.pack(fill="x", pady=(2, 12))

        cur = self.config_manager.get("theme_mode", "Light")
        self.theme_selector.set("Branco (Light)" if cur == "Light" else "Preto (Dark)")

        self.sw_glow = self._create_switch(scroll, "Efeitos de Brilho (Glow)", "glow_effects")

    def _on_theme_select(self, choice: str) -> None:
        new_theme = "Light" if "Branco" in choice else "Dark"
        self.current_theme_str = new_theme
        ctk.set_appearance_mode(new_theme)
        self.config_manager.set("theme_mode", new_theme)
        self._apply_theme_colors()
        self.enqueue_log(f"Tema alterado para: {new_theme.upper()}", "INFO")

    def _apply_theme_colors(self) -> None:
        """Ajusta cores de alto contraste de acordo com o tema selecionado."""
        is_dark = (self.current_theme_str == "Dark")
        bg_col = "#0a0a0a" if is_dark else "#F8FAFC"
        self.configure(fg_color=bg_col)

    def _populate_config_ia(self, tab: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(scroll, text="Modelo de Inteligência Artificial", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(4, 2))

        self.combo_model = ctk.CTkComboBox(
            scroll,
            values=["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4o-mini"],
            command=lambda v: self.config_manager.set("model_name", v)
        )
        self.combo_model.pack(fill="x", pady=(0, 10))
        self.combo_model.set(self.config_manager.get("model_name", "gemini-2.5-flash"))

        ctk.CTkLabel(scroll, text="Dica do Modo de Questão", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(4, 2))
        self.combo_mode_hint = ctk.CTkComboBox(
            scroll,
            values=["Detecção Automática", "Múltipla Escolha", "Verdadeiro ou Falso", "Caixa de Seleção / Checkbox", "Discursiva / Texto"],
            command=lambda v: self.config_manager.set("question_mode_hint", v)
        )
        self.combo_mode_hint.pack(fill="x", pady=(0, 10))
        self.combo_mode_hint.set(self.config_manager.get("question_mode_hint", "Detecção Automática"))

        ctk.CTkLabel(scroll, text="Dica de Idioma da Resposta", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(4, 2))
        self.combo_lang_hint = ctk.CTkComboBox(
            scroll,
            values=["Auto-Detectar", "Português", "Inglês", "Espanhol"],
            command=lambda v: self.config_manager.set("language_hint", v)
        )
        self.combo_lang_hint.pack(fill="x", pady=(0, 10))
        self.combo_lang_hint.set(self.config_manager.get("language_hint", "Auto-Detectar"))

        self._create_switch(scroll, "Visão Computacional Ativa (Recorte e classificação)", "enable_computer_vision")

    def _populate_config_sistema(self, tab: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(scroll, text="Motor de Execução", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(4, 2))
        combo_engine = ctk.CTkComboBox(
            scroll,
            values=["Inteligente (Auto-Híbrido: Visão + Cliques ou Ponte DOM)", "Apenas Visão"],
            command=lambda v: self.config_manager.set("execution_engine", v)
        )
        combo_engine.pack(fill="x", pady=(0, 10))
        combo_engine.set(self.config_manager.get("execution_engine", "Inteligente (Auto-Híbrido: Visão + Cliques ou Ponte DOM)"))

        self._create_switch(scroll, "Auto Scroll nos Logs", "auto_scroll_logs")

        # Seção Dados Locais
        ctk.CTkLabel(scroll, text="Dados Locais do Cérebro", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(10, 4))

        btn_export = ctk.CTkButton(scroll, text="📦 Exportar Dados (ZIP)", command=self._cmd_export_cerebro)
        btn_export.pack(fill="x", pady=4)

        # Seção Zona de Risco
        ctk.CTkLabel(scroll, text="Zona de Risco", font=ctk.CTkFont(size=13, weight="bold"), text_color="#DC2626").pack(anchor="w", pady=(14, 4))

        btn_reset_all = ctk.CTkButton(
            scroll,
            text="⚠️ Resetar Todos os Dados e Memória",
            fg_color="#DC2626",
            hover_color="#B91C1C",
            command=self._cmd_reset_all_data
        )
        btn_reset_all.pack(fill="x", pady=4)

    def _cmd_export_cerebro(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("Arquivo ZIP", "*.zip")], title="Exportar Cérebro")
        if path:
            ok = self.cerebro_manager.export_cerebro_zip(path)
            if ok:
                messagebox.showinfo("Exportação", "Dados do Cérebro exportados com sucesso!")
            else:
                messagebox.showerror("Exportação", "Falha ao gerar o arquivo ZIP.")

    def _cmd_reset_all_data(self) -> None:
        if messagebox.askyesno("Zona de Risco", "Tem certeza que deseja apagar permanentemente todas as sessões, mídias e índice do Cérebro?"):
            self.cerebro_manager.clear_all_data()
            self.metrics_tracker.clear()
            self._reload_cerebro_tree()
            self._refresh_metricas_ui()
            self.enqueue_log("Todos os dados do Cérebro foram resetados com sucesso.", "WARNING")

    # =========================================================================
    # CONTROLES GLOBAIS, CALIBRAÇÃO E COMANDOS
    # =========================================================================
    def _cmd_toggle_autopilot(self) -> None:
        if self.engine.is_running:
            self.engine.stop()
            self.btn_autopilot.configure(text="✨ RESOLVER AUTOPILOT", fg_color="#2563EB")
        else:
            ok = self.engine.start()
            if ok:
                self.btn_autopilot.configure(text="⏸ PAUSAR AUTOPILOT", fg_color="#F59E0B")

    def _on_toggle_topmost(self) -> None:
        val = bool(self.switch_topmost.get())
        self.attributes("-topmost", val)
        self.config_manager.set("always_on_top", val)

    def _start_area_selection(self) -> None:
        self.withdraw()
        self.after(250, lambda: ScreenAreaSelector(self, self._on_area_selected))

    def _on_area_selected(self, x: int, y: int, w: int, h: int) -> None:
        self.deiconify()
        self.config_manager.update_quiz_region(x, y, w, h)
        self.lbl_res_area.configure(text=f"Área: X={x} Y={y} ({w}x{h} px)", text_color="#10B981")
        self.enqueue_log(f"Área calibrada: [{x}, {y}, {w}, {h}].", "SUCCESS")

    def _start_next_button_selection(self) -> None:
        self.withdraw()
        self.after(250, lambda: PointSelector(self, self._on_next_selected, "Clique no Botão Próximo"))

    def _on_next_selected(self, x: int, y: int) -> None:
        self.deiconify()
        self.config_manager.update_next_button(x, y)
        self.lbl_res_next.configure(text=f"Botão Próximo: X={x} Y={y}", text_color="#10B981")
        self.enqueue_log(f"Botão Próximo mapeado: ({x}, {y}).", "SUCCESS")

    def update_status_badge(self, state: str) -> None:
        def apply():
            self.lbl_status_bar.configure(text=f"Estado: {state}")
            if state in ("PRONTO", "EXECUTANDO"):
                self.status_pill.configure(text=state, text_color="#16A34A", fg_color=("#DCFCE7", "#14532D"))
            elif state in ("ANALISANDO", "RESPONDENDO"):
                self.status_pill.configure(text=state, text_color="#2563EB", fg_color=("#DBEAFE", "#1E3A8A"))
            elif state == "SIMULAÇÃO DRY-RUN":
                self.status_pill.configure(text="DRY-RUN", text_color="#F59E0B", fg_color=("#FEF3C7", "#78350F"))
            elif state == "PAUSADO":
                self.status_pill.configure(text="PAUSADO", text_color="#EAB308", fg_color=("#FEF9C3", "#713F12"))
            else:
                self.status_pill.configure(text="PARADO", text_color="#EF4444", fg_color=("#FEE2E2", "#3B1E1E"))
        self.after(0, apply)

    def enqueue_log(self, message: str, level: str = "INFO") -> None:
        def apply():
            now = datetime.datetime.now().strftime("%H:%M:%S")
            prefix = {
                "INFO": "[INFO]",
                "SUCCESS": "[OK]",
                "WARNING": "[AVISO]",
                "ERROR": "[ERRO]"
            }.get(level, "[LOG]")
            self.txt_terminal_output.insert("end", f"[{now}] {prefix} {message}\n")
            if self.config_manager.get("auto_scroll_logs", True):
                self.txt_terminal_output.see("end")
        self.after(0, apply)

    def _setup_hotkeys(self) -> None:
        self.bind("<F8>", lambda e: self._cmd_toggle_autopilot())
        self.bind("<Escape>", lambda e: self.engine.stop())

        try:
            import keyboard
            keyboard.add_hotkey("f8", lambda: self.after(0, self._cmd_toggle_autopilot))
            keyboard.add_hotkey("esc", lambda: self.after(0, self.engine.stop))
        except Exception:
            pass

    def _on_close(self) -> None:
        self.engine.stop()
        self.destroy()
