"""
Módulo de Interface Gráfica Moderna (GUI) - EasyQuiz Desktop
Desenvolvido em CustomTkinter com modo escuro nativo, calibração visual e logs em tempo real.
"""

import datetime
import tkinter as tk
from typing import Optional
import customtkinter as ctk

from config_manager import ConfigManager
from ai_service import AIService
from automation import AutomationEngine
from overlay import ScreenAreaSelector, PointSelector

# Configuração global de aparência
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class EasyQuizGUI(ctk.CTk):
    """Janela principal da aplicação desktop EasyQuiz."""

    def __init__(self, config_manager: ConfigManager, ai_service: AIService):
        super().__init__()

        self.config_manager = config_manager
        self.ai_service = ai_service

        # Inicialização do motor de automação
        self.engine = AutomationEngine(
            config_manager=self.config_manager,
            ai_service=self.ai_service,
            log_callback=self.enqueue_log,
            status_callback=self.update_status_badge
        )

        # Configurações da Janela
        self.title("EasyQuiz Desktop - Automação Inteligente de Quizzes")
        self.geometry("1060x780")
        self.minsize(980, 700)

        # Configura grid responsivo
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Construção dos componentes visuais
        self._build_header()
        self._build_left_panel()
        self._build_right_panel()

        # Vinculação de Hotkeys Globais e Locais
        self._setup_hotkeys()

        # Carrega dados salvos para a interface
        self._load_saved_ui_state()

        # Protocolo de fechamento
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.enqueue_log("Sistema EasyQuiz Desktop inicializado com sucesso.", "SUCCESS")
        self.enqueue_log("Pressione [F8] para Iniciar/Pausar e [ESC] para Parada de Emergência.", "INFO")

    def _build_header(self) -> None:
        """Cria a barra superior de cabeçalho e indicador de status."""
        header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#181B20")
        header_frame.grid(row=0, column=0, columnspan=2, padx=16, pady=(16, 8), sticky="ew")

        # Título e Descrição
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=12)

        title_label = ctk.CTkLabel(
            title_box,
            text="EASYQUIZ DESKTOP",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#00E5FF"
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            title_box,
            text="Automação Inteligente com Visão Computacional e IA Multimodal",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#90A4AE"
        )
        subtitle_label.pack(anchor="w")

        # Badge de Status de Execução
        self.status_badge = ctk.CTkLabel(
            header_frame,
            text="● PARADO",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#FF5252",
            fg_color="#261C1C",
            corner_radius=8,
            padx=16,
            pady=8
        )
        self.status_badge.pack(side="right", padx=16, pady=12)

    def _build_left_panel(self) -> None:
        """Cria os cartões de configurações e calibração no painel esquerdo."""
        left_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        left_container.grid(row=1, column=0, padx=(16, 8), pady=8, sticky="nsew")

        # CARD 1: Configuração de IA
        ai_card = ctk.CTkFrame(left_container, corner_radius=10, fg_color="#1E222B")
        ai_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            ai_card,
            text="🤖 Configuração de Inteligência Artificial",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#E0E6ED"
        ).pack(anchor="w", padx=14, pady=(12, 6))

        # Provedor e Modelo
        prov_row = ctk.CTkFrame(ai_card, fg_color="transparent")
        prov_row.pack(fill="x", padx=14, pady=4)

        ctk.CTkLabel(prov_row, text="Provedor:", width=70, anchor="w").pack(side="left")
        self.provider_var = ctk.StringVar(value="Google Gemini")
        self.provider_combo = ctk.CTkOptionMenu(
            prov_row,
            values=["Google Gemini", "OpenAI"],
            variable=self.provider_var,
            command=self._on_provider_change,
            width=140
        )
        self.provider_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(prov_row, text="Modelo:", width=50, anchor="w").pack(side="left")
        self.model_var = ctk.StringVar(value="gemini-2.5-flash")
        self.model_combo = ctk.CTkComboBox(
            prov_row,
            values=["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
            variable=self.model_var
        )
        self.model_combo.pack(side="left", fill="x", expand=True)

        # API Key
        key_label = ctk.CTkLabel(ai_card, text="Chave de API (Key):")
        key_label.pack(anchor="w", padx=14, pady=(8, 2))

        key_row = ctk.CTkFrame(ai_card, fg_color="transparent")
        key_row.pack(fill="x", padx=14, pady=(0, 10))

        self.key_entry = ctk.CTkEntry(
            key_row,
            placeholder_text="Cole sua API Key aqui...",
            show="*",
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.show_key_btn = ctk.CTkButton(
            key_row,
            text="👁",
            width=36,
            command=self._toggle_show_key,
            fg_color="#2E3440",
            hover_color="#3B4252"
        )
        self.show_key_btn.pack(side="left")

        # Botão Salvar
        self.save_btn = ctk.CTkButton(
            ai_card,
            text="Salvar Configurações de IA",
            command=self._save_ai_config,
            fg_color="#00897B",
            hover_color="#00796B",
            font=ctk.CTkFont(weight="bold")
        )
        self.save_btn.pack(fill="x", padx=14, pady=(0, 14))

        # CARD 2: Calibração de Tela
        calib_card = ctk.CTkFrame(left_container, corner_radius=10, fg_color="#1E222B")
        calib_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            calib_card,
            text="📐 Calibração e Regiões da Tela",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#E0E6ED"
        ).pack(anchor="w", padx=14, pady=(12, 6))

        # Botão Área do Quiz
        btn_area_row = ctk.CTkFrame(calib_card, fg_color="transparent")
        btn_area_row.pack(fill="x", padx=14, pady=6)

        self.btn_select_area = ctk.CTkButton(
            btn_area_row,
            text="🔍 Selecionar Área do Quiz",
            command=self._start_area_selection,
            fg_color="#1E88E5",
            hover_color="#1565C0",
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_select_area.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.lbl_area_status = ctk.CTkLabel(
            calib_card,
            text="Área: Não definida",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#FFB74D"
        )
        self.lbl_area_status.pack(anchor="w", padx=16, pady=(0, 8))

        # Botão Próxima Pergunta
        btn_next_row = ctk.CTkFrame(calib_card, fg_color="transparent")
        btn_next_row.pack(fill="x", padx=14, pady=6)

        self.btn_select_next = ctk.CTkButton(
            btn_next_row,
            text="🎯 Definir Botão Próximo",
            command=self._start_next_button_selection,
            fg_color="#3949AB",
            hover_color="#283593",
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_select_next.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.lbl_next_status = ctk.CTkLabel(
            calib_card,
            text="Botão Próximo: Não definido",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#90A4AE"
        )
        self.lbl_next_status.pack(anchor="w", padx=16, pady=(0, 12))

        # CARD 3: Configurações de Automação
        auto_card = ctk.CTkFrame(left_container, corner_radius=10, fg_color="#1E222B")
        auto_card.pack(fill="x")

        ctk.CTkLabel(
            auto_card,
            text="⏱️ Parâmetros de Temporização",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#E0E6ED"
        ).pack(anchor="w", padx=14, pady=(12, 6))

        # Delay pós-resposta
        delay_header = ctk.CTkFrame(auto_card, fg_color="transparent")
        delay_header.pack(fill="x", padx=14, pady=(4, 0))

        ctk.CTkLabel(delay_header, text="Espera antes de avançar:").pack(side="left")
        self.lbl_delay_val = ctk.CTkLabel(delay_header, text="2.5 s", font=ctk.CTkFont(weight="bold"))
        self.lbl_delay_val.pack(side="right")

        self.slider_delay = ctk.CTkSlider(
            auto_card,
            from_=0.5,
            to=10.0,
            number_of_steps=95,
            command=self._on_delay_slider_change
        )
        self.slider_delay.pack(fill="x", padx=14, pady=(0, 10))

        # Opções Adicionais
        self.check_auto_advance = ctk.CTkCheckBox(
            auto_card,
            text="Avançar automaticamente para a próxima questão",
            command=self._save_checkboxes
        )
        self.check_auto_advance.pack(anchor="w", padx=14, pady=4)

        self.check_smooth_mouse = ctk.CTkCheckBox(
            auto_card,
            text="Movimento suave e humanizado do mouse",
            command=self._save_checkboxes
        )
        self.check_smooth_mouse.pack(anchor="w", padx=14, pady=(4, 14))

    def _build_right_panel(self) -> None:
        """Cria o painel de controles principais e console de logs à direita."""
        right_container = ctk.CTkFrame(self, fg_color="transparent")
        right_container.grid(row=1, column=1, padx=(8, 16), pady=8, sticky="nsew")
        right_container.grid_rowconfigure(1, weight=1)
        right_container.grid_columnconfigure(0, weight=1)

        # CARD CONTROLES
        ctrl_card = ctk.CTkFrame(right_container, corner_radius=10, fg_color="#1E222B")
        ctrl_card.grid(row=0, column=0, fill="x", pady=(0, 12))

        ctk.CTkLabel(
            ctrl_card,
            text="🎮 Painel de Controle de Execução",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#E0E6ED"
        ).pack(anchor="w", padx=14, pady=(12, 8))

        btn_grid = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        btn_grid.pack(fill="x", padx=14, pady=(0, 8))
        btn_grid.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_start = ctk.CTkButton(
            btn_grid,
            text="▶ Iniciar (F8)",
            command=self._cmd_start,
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            height=42,
            font=ctk.CTkFont(weight="bold", size=14)
        )
        self.btn_start.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.btn_pause = ctk.CTkButton(
            btn_grid,
            text="⏸ Pausar (F8)",
            command=self._cmd_pause,
            fg_color="#F57F17",
            hover_color="#E65100",
            height=42,
            font=ctk.CTkFont(weight="bold", size=14)
        )
        self.btn_pause.grid(row=0, column=1, padx=6, sticky="ew")

        self.btn_stop = ctk.CTkButton(
            btn_grid,
            text="⏹ Parar (ESC)",
            command=self._cmd_stop,
            fg_color="#C62828",
            hover_color="#8E0000",
            height=42,
            font=ctk.CTkFont(weight="bold", size=14)
        )
        self.btn_stop.grid(row=0, column=2, padx=(6, 0), sticky="ew")

        hint_label = ctk.CTkLabel(
            ctrl_card,
            text="💡 Dica: Use [F8] no teclado para Iniciar/Pausar e [ESC] como emergência.",
            font=ctk.CTkFont(size=11),
            text_color="#90A4AE"
        )
        hint_label.pack(anchor="w", padx=14, pady=(0, 10))

        # CARD LOGS E STATUS
        log_card = ctk.CTkFrame(right_container, corner_radius=10, fg_color="#1E222B")
        log_card.grid(row=1, column=0, fill="both", sticky="nsew")
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.grid(row=0, column=0, fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            log_header,
            text="📜 Log de Execução em Tempo Real",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#E0E6ED"
        ).pack(side="left")

        btn_clear_log = ctk.CTkButton(
            log_header,
            text="Limpar",
            width=70,
            height=26,
            command=self._clear_logs,
            fg_color="#2E3440",
            hover_color="#3B4252"
        )
        btn_clear_log.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            log_card,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#12151B",
            text_color="#D8DEE9",
            wrap="word",
            corner_radius=8
        )
        self.log_textbox.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="nsew")

    def _setup_hotkeys(self) -> None:
        """Registra hotkeys globais no sistema operacional e atalhos na janela."""
        self.bind("<F8>", lambda e: self.engine.toggle_play_pause())
        self.bind("<Escape>", lambda e: self.engine.stop())

        # Tenta registrar atalhos globais via biblioteca keyboard
        try:
            import keyboard
            keyboard.add_hotkey("f8", lambda: self.after(0, self.engine.toggle_play_pause))
            keyboard.add_hotkey("esc", lambda: self.after(0, self.engine.stop))
        except Exception as e:
            self.enqueue_log(f"Aviso de Atalhos Globais: {e}. Atalhos disponíveis quando a janela estiver focada.", "WARNING")

    def _load_saved_ui_state(self) -> None:
        """Restaura todos os valores gravados no config.json para os campos visuais."""
        cfg = self.config_manager.config_data

        # Provedor e modelo
        prov = "Google Gemini" if cfg.get("api_provider") == "gemini" else "OpenAI"
        self.provider_var.set(prov)
        self._on_provider_change(prov)
        self.model_var.set(cfg.get("model_name", "gemini-2.5-flash"))

        # API Key
        key = cfg.get("api_key", "")
        if key:
            self.key_entry.insert(0, key)

        # Região do Quiz
        region = cfg.get("quiz_region", {})
        if region.get("configured", False):
            self.lbl_area_status.configure(
                text=f"Área: X={region['x']} Y={region['y']} ({region['width']}x{region['height']} px)",
                text_color="#00E676"
            )

        # Botão Próximo
        nxt = cfg.get("next_button", {})
        if nxt.get("configured", False):
            self.lbl_next_status.configure(
                text=f"Botão Próximo: X={nxt['x']} Y={nxt['y']}",
                text_color="#00E676"
            )

        # Slider de Delay
        delay = float(cfg.get("action_delay", 2.5))
        self.slider_delay.set(delay)
        self.lbl_delay_val.configure(text=f"{delay:.1f} s")

        # Checkboxes
        if cfg.get("auto_advance", True):
            self.check_auto_advance.select()
        else:
            self.check_auto_advance.deselect()

        if cfg.get("smooth_mouse", True):
            self.check_smooth_mouse.select()
        else:
            self.check_smooth_mouse.deselect()

    def _on_provider_change(self, choice: str) -> None:
        """Atualiza a lista de modelos recomendados de acordo com o provedor escolhido."""
        if choice == "Google Gemini":
            models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
            self.model_combo.configure(values=models)
            if self.model_var.get() not in models:
                self.model_var.set("gemini-2.5-flash")
        else:
            models = ["gpt-4o-mini", "gpt-4o"]
            self.model_combo.configure(values=models)
            if self.model_var.get() not in models:
                self.model_var.set("gpt-4o-mini")

    def _toggle_show_key(self) -> None:
        """Alterna a exibição oculta/visível da Chave de API."""
        if self.key_entry.cget("show") == "*":
            self.key_entry.configure(show="")
            self.show_key_btn.configure(text="🔒")
        else:
            self.key_entry.configure(show="*")
            self.show_key_btn.configure(text="👁")

    def _save_ai_config(self) -> None:
        """Salva a chave de API, provedor e modelo selecionados no disco."""
        prov_key = "gemini" if self.provider_var.get() == "Google Gemini" else "openai"
        key_val = self.key_entry.get().strip()
        model_val = self.model_var.get().strip()

        self.config_manager.set("api_provider", prov_key, auto_save=False)
        self.config_manager.set("api_key", key_val, auto_save=False)
        self.config_manager.set("model_name", model_val, auto_save=True)

        self.ai_service.update_credentials(prov_key, key_val, model_val)
        self.enqueue_log("Configurações de Inteligência Artificial salvas com sucesso.", "SUCCESS")

    def _on_delay_slider_change(self, val: float) -> None:
        """Atualiza o label e o arquivo de configuração ao mover o slider."""
        rounded = round(val, 1)
        self.lbl_delay_val.configure(text=f"{rounded:.1f} s")
        self.config_manager.set("action_delay", rounded)

    def _save_checkboxes(self) -> None:
        """Salva o estado das caixas de seleção."""
        self.config_manager.set("auto_advance", bool(self.check_auto_advance.get()), auto_save=False)
        self.config_manager.set("smooth_mouse", bool(self.check_smooth_mouse.get()), auto_save=True)

    def _start_area_selection(self) -> None:
        """Oculta temporariamente a janela e abre a sobreposição de seleção de área."""
        self.withdraw()
        self.after(250, lambda: ScreenAreaSelector(self, self._on_area_selected))

    def _on_area_selected(self, x: int, y: int, w: int, h: int) -> None:
        """Recebe as coordenadas da área selecionada e atualiza a interface."""
        self.deiconify()
        self.config_manager.update_quiz_region(x, y, w, h)
        self.lbl_area_status.configure(
            text=f"Área: X={x} Y={y} ({w}x{h} px)",
            text_color="#00E676"
        )
        self.enqueue_log(f"Área do quiz definida com sucesso: [{x}, {y}, {w}, {h}].", "SUCCESS")

    def _start_next_button_selection(self) -> None:
        """Oculta temporariamente a janela e abre a captura do botão próximo."""
        self.withdraw()
        self.after(250, lambda: PointSelector(self, self._on_next_button_selected, "Clique no Botão Próximo"))

    def _on_next_button_selected(self, x: int, y: int) -> None:
        """Recebe as coordenadas do botão próximo e atualiza a interface."""
        self.deiconify()
        self.config_manager.update_next_button(x, y)
        self.lbl_next_status.configure(
            text=f"Botão Próximo: X={x} Y={y}",
            text_color="#00E676"
        )
        self.enqueue_log(f"Botão Próximo calibrado na coordenada: ({x}, {y}).", "SUCCESS")

    def _cmd_start(self) -> None:
        self.engine.start()

    def _cmd_pause(self) -> None:
        self.engine.pause()

    def _cmd_stop(self) -> None:
        self.engine.stop()

    def update_status_badge(self, state: str) -> None:
        """Atualiza a cor e texto do badge de status de forma thread-safe."""
        def apply():
            if state == "EXECUTANDO":
                self.status_badge.configure(text="● EXECUTANDO", text_color="#00E676", fg_color="#182E20")
            elif state == "PAUSADO":
                self.status_badge.configure(text="● PAUSADO", text_color="#FFD600", fg_color="#2E2818")
            else:
                self.status_badge.configure(text="● PARADO", text_color="#FF5252", fg_color="#261C1C")
        self.after(0, apply)

    def enqueue_log(self, message: str, level: str = "INFO") -> None:
        """Enfileira mensagem formatada no console de logs com timestamp."""
        def apply():
            now = datetime.datetime.now().strftime("%H:%M:%S")
            prefix = {
                "INFO": "ℹ️ [INFO]",
                "SUCCESS": "✅ [OK]",
                "WARNING": "⚠️ [AVISO]",
                "ERROR": "❌ [ERRO]"
            }.get(level, "[LOG]")

            formatted_msg = f"[{now}] {prefix} {message}\n"
            self.log_textbox.insert("end", formatted_msg)
            self.log_textbox.see("end")

        self.after(0, apply)

    def _clear_logs(self) -> None:
        """Limpa a caixa de texto de logs."""
        self.log_textbox.delete("1.0", "end")

    def _on_close(self) -> None:
        """Encerra a automação e fecha a aplicação seguramente."""
        self.engine.stop()
        self.destroy()
