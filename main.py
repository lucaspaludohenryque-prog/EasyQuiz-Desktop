"""
Ponto de Entrada e Interface Principal - Mastering Study Quiz
Painel Vertical Dockable (CustomTkinter) com os controles da Etapa 2:
1. Botão 'Selecionar Área do Quiz' (Overlay Transparente com Bounding Box Vermelho).
2. Botão 'Mapear Botão Próximo' (Captura de Coordenada).
3. Botão '✨ Iniciar Autopilot' com Thread em background, conversão de coordenadas,
   cliques suaves com PyAutoGUI e avanço automático.
4. Atalhos globais: F8 (Iniciar/Pausar), ESC (Parada de Emergência) e Alt+Q (Modo Furtivo).
5. Seletor de Temas: Light (Branco Clean Padrão) e Dark (Mega Black).
"""

import os
import sys
import time
import ctypes
import threading
from datetime import datetime
from typing import Optional, Dict, Any

from PIL import Image
import customtkinter as ctk

try:
    import keyboard
except ImportError:
    keyboard = None

from config_manager import ConfigManager
from brain_storage import BrainStorage
from ai_service import AIService, QuizSolutionResult
from automation import (
    open_crop_selector,
    open_next_button_mapper,
    capture_screen_region,
    smooth_click,
    click_next_button
)

# Configurações de tema padrão inicial: Light (Branco Clean)
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


def setup_windows_dpi_awareness() -> None:
    """Configura DPI Awareness no Windows para alinhamento sub-pixel no RPA."""
    if sys.platform.startswith("win"):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


class MasteringStudyQuizApp(ctk.CTk):
    """Interface Gráfica e Orquestrador Principal do Mastering Study Quiz."""

    VERSION = "v3.9.0"

    def __init__(self):
        super().__init__()

        # Inicializa serviços do motor
        self.config_manager = ConfigManager("config.json")
        self.brain_storage = BrainStorage()
        self.ai_service = AIService(
            config_manager=self.config_manager,
            brain_storage=self.brain_storage
        )

        # Estado da Thread do Autopilot
        self._autopilot_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._is_running = False
        self._is_stealth_hidden = False

        # Configurações de Janela Dockable Vertical
        self.title(f"Mastering Study Quiz {self.VERSION}")
        self.geometry("460x830")
        self.minsize(420, 720)

        # Always on Top
        self.is_always_on_top = self.config_manager.get("always_on_top", True)
        self.attributes("-topmost", self.is_always_on_top)

        # Aplica o tema salvo (Light padrão ou Dark)
        saved_theme = self.config_manager.get("theme_mode", "Light")
        ctk.set_appearance_mode(saved_theme)

        # Constrói os componentes visuais
        self._build_ui()

        # Registra Atalhos Globais
        self._register_hotkeys()

        # Trata o fechamento da janela
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.log("Sistema inicializado e pronto para operação.", "INFO")

    def _build_ui(self) -> None:
        """Constrói o layout modular da interface."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # Área do terminal expande

        # 1. Cabeçalho com Logo, Status e Botão Pin
        self._build_header()

        # 2. Painel de Calibração (Área do Quiz & Botão Próximo)
        self._build_calibration_panel()

        # 3. Painel de Controle Principal (Botão Autopilot)
        self._build_control_panel()

        # 4. Monitor em Tempo Real (Última Resposta / Cérebro)
        self._build_live_monitor()

        # 5. Terminal de Logs em Tempo Real
        self._build_terminal_panel()

    def _build_header(self) -> None:
        header_frame = ctk.CTkFrame(self, corner_radius=12)
        header_frame.grid(row=0, column=0, padx=14, pady=(12, 6), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        top_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=10)

        # Logo e Título
        title_box = ctk.CTkFrame(top_row, fg_color="transparent")
        title_box.pack(side="left")

        title_lbl = ctk.CTkLabel(
            title_box,
            text="Mastering Study Quiz",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#0284C7"
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            title_box,
            text=f"{self.VERSION} • Motor Híbrido RPA + Vision",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        sub_lbl.pack(anchor="w")

        # Ações Rápidas (Pin + Tema)
        actions_box = ctk.CTkFrame(top_row, fg_color="transparent")
        actions_box.pack(side="right", padx=(10, 0))

        # Botão Pin (Always on Top)
        self.pin_btn = ctk.CTkButton(
            actions_box,
            text="📌 Fixar" if self.is_always_on_top else "📍 Solto",
            width=65,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#0284C7" if self.is_always_on_top else "#64748B",
            command=self.toggle_always_on_top
        )
        self.pin_btn.pack(side="left", padx=4)

        # Seletor de Tema
        current_mode = self.config_manager.get("theme_mode", "Light")
        self.theme_switch = ctk.CTkOptionMenu(
            actions_box,
            values=["Light", "Dark"],
            width=75,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_theme_changed
        )
        self.theme_switch.set(current_mode)
        self.theme_switch.pack(side="left", padx=4)

        # Badge de Status
        status_bar = ctk.CTkFrame(header_frame, fg_color="transparent")
        status_bar.pack(fill="x", padx=12, pady=(0, 10))

        self.status_badge = ctk.CTkLabel(
            status_bar,
            text="● PRONTO",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#16A34A"
        )
        self.status_badge.pack(side="left")

        self.hotkey_info = ctk.CTkLabel(
            status_bar,
            text="[F8] Iniciar/Pausar  |  [ESC] Parar  |  [Alt+Q] Ocultar",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.hotkey_info.pack(side="right")

    def _build_calibration_panel(self) -> None:
        calib_frame = ctk.CTkFrame(self, corner_radius=12)
        calib_frame.grid(row=1, column=0, padx=14, pady=6, sticky="ew")

        lbl_section = ctk.CTkLabel(
            calib_frame,
            text="CALIBRAÇÃO E MAPEAMENTO DE TELA",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#64748B"
        )
        lbl_section.pack(anchor="w", padx=14, pady=(10, 4))

        btn_row = ctk.CTkFrame(calib_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=4)

        # Botão 1: Selecionar Área do Quiz
        self.btn_select_region = ctk.CTkButton(
            btn_row,
            text="📐 Selecionar Área do Quiz",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0F172A",
            hover_color="#1E293B",
            command=self.start_region_selection
        )
        self.btn_select_region.pack(side="left", fill="x", expand=True, padx=4)

        # Botão 2: Mapear Botão Próximo
        self.btn_map_next = ctk.CTkButton(
            btn_row,
            text="🎯 Mapear Botão Próximo",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0F172A",
            hover_color="#1E293B",
            command=self.start_next_button_mapping
        )
        self.btn_map_next.pack(side="right", fill="x", expand=True, padx=4)

        # Status das Coordenadas Salvas
        status_coord_row = ctk.CTkFrame(calib_frame, fg_color="transparent")
        status_coord_row.pack(fill="x", padx=14, pady=(4, 10))

        reg = self.config_manager.get("quiz_region", {})
        reg_text = f"Área: ({reg.get('x',0)}, {reg.get('y',0)}, {reg.get('width',0)}x{reg.get('height',0)})" if reg.get("configured") else "Área: Não demarcada"
        self.lbl_region_status = ctk.CTkLabel(
            status_coord_row,
            text=reg_text,
            font=ctk.CTkFont(size=11),
            text_color="#0284C7" if reg.get("configured") else "#EF4444"
        )
        self.lbl_region_status.pack(side="left")

        nxt = self.config_manager.get("next_button", {})
        nxt_text = f"Próximo: ({nxt.get('x',0)}, {nxt.get('y',0)})" if nxt.get("configured") else "Próximo: Não mapeado"
        self.lbl_next_status = ctk.CTkLabel(
            status_coord_row,
            text=nxt_text,
            font=ctk.CTkFont(size=11),
            text_color="#0284C7" if nxt.get("configured") else "#EF4444"
        )
        self.lbl_next_status.pack(side="right")

    def _build_control_panel(self) -> None:
        ctrl_frame = ctk.CTkFrame(self, corner_radius=12)
        ctrl_frame.grid(row=2, column=0, padx=14, pady=6, sticky="ew")

        # Botão Principal Grande: RESOLVER AUTOPILOT
        self.btn_autopilot = ctk.CTkButton(
            ctrl_frame,
            text="✨ INICIAR AUTOPILOT (F8)",
            height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#16A34A",
            hover_color="#15803D",
            command=self.toggle_autopilot
        )
        self.btn_autopilot.pack(fill="x", padx=14, pady=(12, 6))

        # Botão de Parada de Emergência
        self.btn_stop = ctk.CTkButton(
            ctrl_frame,
            text="⛔ PARADA DE EMERGÊNCIA (ESC)",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#DC2626",
            hover_color="#B91C1C",
            command=self.emergency_stop
        )
        self.btn_stop.pack(fill="x", padx=14, pady=(0, 12))

    def _build_live_monitor(self) -> None:
        live_frame = ctk.CTkFrame(self, corner_radius=12)
        live_frame.grid(row=3, column=0, padx=14, pady=6, sticky="ew")

        title_row = ctk.CTkFrame(live_frame, fg_color="transparent")
        title_row.pack(fill="x", padx=14, pady=(10, 4))

        lbl_live = ctk.CTkLabel(
            title_row,
            text="CÉREBRO DA IA • MONITOR AO VIVO",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#64748B"
        )
        lbl_live.pack(side="left")

        self.lbl_token_badge = ctk.CTkLabel(
            title_row,
            text="0 Tokens Consumidos",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#0284C7"
        )
        self.lbl_token_badge.pack(side="right")

        # Card de Resumo da Última Questão
        summary_box = ctk.CTkFrame(live_frame, fg_color=ctk.ThemeManager.theme["CTkFrame"]["top"])
        summary_box.pack(fill="x", padx=12, pady=(0, 10))

        self.lbl_last_answer = ctk.CTkLabel(
            summary_box,
            text="Nenhuma questão resolvida nesta sessão.",
            font=ctk.CTkFont(size=13, weight="bold"),
            wraplength=380,
            justify="left"
        )
        self.lbl_last_answer.pack(anchor="w", padx=12, pady=(8, 2))

        self.lbl_rationale = ctk.CTkLabel(
            summary_box,
            text="O raciocínio passo a passo da IA aparecerá aqui em tempo real.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=380,
            justify="left"
        )
        self.lbl_rationale.pack(anchor="w", padx=12, pady=(0, 8))

    def _build_terminal_panel(self) -> None:
        term_frame = ctk.CTkFrame(self, corner_radius=12)
        term_frame.grid(row=4, column=0, padx=14, pady=(6, 12), sticky="nsew")
        term_frame.grid_columnconfigure(0, weight=1)
        term_frame.grid_rowconfigure(1, weight=1)

        header_term = ctk.CTkFrame(term_frame, fg_color="transparent")
        header_term.grid(row=0, column=0, padx=12, pady=(8, 4), sticky="ew")

        lbl_t = ctk.CTkLabel(
            header_term,
            text="TERMINAL DE LOGS DO AUTOPILOT",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#64748B"
        )
        lbl_t.pack(side="left")

        btn_clear = ctk.CTkButton(
            header_term,
            text="Limpar",
            width=50,
            height=22,
            font=ctk.CTkFont(size=10),
            fg_color="transparent",
            text_color="gray",
            hover_color="#334155",
            command=self.clear_logs
        )
        btn_clear.pack(side="right")

        # Textbox para logs
        self.log_box = ctk.CTkTextbox(
            term_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.log_box.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="nsew")

    # =========================================================================
    # Ações de Calibração (Recorte e Próximo)
    # =========================================================================
    def start_region_selection(self) -> None:
        """Inicia a ferramenta de recorte com overlay transparente."""
        self.log("Abrindo ferramenta de seleção de área... Arraste o retângulo vermelho.", "INFO")
        # Oculta temporariamente a janela para facilitar o recorte
        self.withdraw()
        time.sleep(0.2)

        def on_selected(x: int, y: int, w: int, h: int) -> None:
            self.deiconify()
            self.config_manager.update_quiz_region(x, y, w, h)
            self.lbl_region_status.configure(
                text=f"Área: ({x}, {y}, {w}x{h}) ✓",
                text_color="#16A34A"
            )
            self.log(f"Área do Quiz demarcada: X={x}, Y={y}, Largura={w}, Altura={h}", "SUCCESS")

        open_crop_selector(self, on_selected)

    def start_next_button_mapping(self) -> None:
        """Inicia o mapeador da coordenada do botão Próximo."""
        self.log("Clique exatamente sobre o botão Próximo / Verificar na tela.", "INFO")
        self.withdraw()
        time.sleep(0.2)

        def on_mapped(x: int, y: int) -> None:
            self.deiconify()
            self.config_manager.update_next_button(x, y)
            self.lbl_next_status.configure(
                text=f"Próximo: ({x}, {y}) ✓",
                text_color="#16A34A"
            )
            self.log(f"Botão Próximo mapeado com sucesso em ({x}, {y}).", "SUCCESS")

        open_next_button_mapper(self, on_mapped)

    # =========================================================================
    # Thread do Autopilot
    # =========================================================================
    def toggle_autopilot(self) -> None:
        """Inicia ou pausa o loop automatizado."""
        if not self._is_running:
            self.start_autopilot()
        else:
            if self._pause_event.is_set():
                self.resume_autopilot()
            else:
                self.pause_autopilot()

    def start_autopilot(self) -> None:
        reg = self.config_manager.get("quiz_region", {})
        if not reg.get("configured"):
            self.log("Atenção: Selecione a Área do Quiz antes de iniciar!", "WARN")
            self.start_region_selection()
            return

        key = self.config_manager.get_active_api_key()
        if not key:
            self.log("Atenção: Nenhuma chave de API configurada no aplicativo!", "WARN")

        self._is_running = True
        self._stop_event.clear()
        self._pause_event.clear()

        self.btn_autopilot.configure(
            text="⏸ PAUSAR AUTOPILOT (F8)",
            fg_color="#D97706",
            hover_color="#B45309"
        )
        self.set_status("AUTOPILOT ATIVO", "#16A34A")
        self.log("Loop Autopilot iniciado. Pressione F8 para pausar ou ESC para parar.", "SUCCESS")

        self._autopilot_thread = threading.Thread(target=self._autopilot_loop, daemon=True)
        self._autopilot_thread.start()

    def pause_autopilot(self) -> None:
        self._pause_event.set()
        self.btn_autopilot.configure(
            text="▶ RETOMAR AUTOPILOT (F8)",
            fg_color="#16A34A",
            hover_color="#15803D"
        )
        self.set_status("PAUSADO", "#D97706")
        self.log("Autopilot pausado pelo usuário.", "WARN")

    def resume_autopilot(self) -> None:
        self._pause_event.clear()
        self.btn_autopilot.configure(
            text="⏸ PAUSAR AUTOPILOT (F8)",
            fg_color="#D97706",
            hover_color="#B45309"
        )
        self.set_status("AUTOPILOT ATIVO", "#16A34A")
        self.log("Autopilot retomado.", "INFO")

    def emergency_stop(self) -> None:
        """Parada de emergência imediata acionada por botão ou tecla ESC."""
        self._stop_event.set()
        self._is_running = False
        self.btn_autopilot.configure(
            text="✨ INICIAR AUTOPILOT (F8)",
            fg_color="#16A34A",
            hover_color="#15803D"
        )
        self.set_status("PARADO", "#EF4444")
        self.log("Parada de emergência executada (ESC).", "WARN")

    def _autopilot_loop(self) -> None:
        """
        Loop Principal do Robô:
        Tira print -> Manda pro ai_service -> Converte coordenadas -> Clica -> Avança.
        """
        while self._is_running and not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.2)
                continue

            try:
                # 1. Recupera região de captura
                reg = self.config_manager.get("quiz_region", {})
                rx = int(reg["x"])
                ry = int(reg["y"])
                rw = int(reg["width"])
                rh = int(reg["height"])

                # 2. Captura de tela rápida via mss
                self.set_status("ANALISANDO...", "#0284C7")
                self.log(f"Capturando região ({rx}, {ry}, {rw}x{rh})...", "INFO")
                img = capture_screen_region(rx, ry, rw, rh)

                # 3. Envia para o motor de IA (ai_service)
                self.log("Enviando questão para o Gemini 2.5 Flash...", "INFO")
                result = self.ai_service.resolve_question_image(img)

                if not result.success:
                    self.log(f"Erro na análise da IA: {result.error_message}", "ERROR")
                    self.set_status("ERRO NA IA", "#EF4444")
                    if not self._sleep_interruptible(3.0):
                        break
                    continue

                # 4. Atualiza informações visuais na GUI
                self._update_live_ui(result)

                # 5. Converte porcentagens relativas em coordenadas absolutas de tela
                target_x = rx + int(result.x_percent * rw)
                target_y = ry + int(result.y_percent * rh)

                self.log(f"Alternativa: '{result.resposta}' | Alvo absoluto: ({target_x}, {target_y})", "SUCCESS")
                self.set_status("RESPONDENDO...", "#8B5CF6")

                # 6. Movimento suave e clique na alternativa
                smooth_click(target_x, target_y, duration=0.28)

                # Delay pós-resposta configurado
                action_delay = float(self.config_manager.get("action_delay", 2.0))
                self.log(f"Aguardando delay pós-resposta ({action_delay}s)...", "INFO")
                if not self._sleep_interruptible(action_delay):
                    break

                # 7. Avanço Automático para o Próximo Item
                next_btn = self.config_manager.get("next_button", {})
                auto_adv = self.config_manager.get("auto_advance", True)

                if auto_adv and next_btn.get("configured"):
                    nx = int(next_btn["x"])
                    ny = int(next_btn["y"])
                    self.log(f"Avançando questão: clicando em ({nx}, {ny})...", "INFO")
                    click_next_button(nx, ny, delay_after=1.2)

                    trans_delay = float(self.config_manager.get("transition_delay", 1.2))
                    self.log(f"Aguardando carregamento da nova questão ({trans_delay}s)...", "INFO")
                    if not self._sleep_interruptible(trans_delay):
                        break
                else:
                    self.log("Avanço concluído. Aguardando novo ciclo...", "INFO")
                    if not self._sleep_interruptible(2.0):
                        break

            except Exception as e:
                self.log(f"Exceção no ciclo do Autopilot: {e}", "ERROR")
                if not self._sleep_interruptible(3.0):
                    break

        self._is_running = False
        self.set_status("PRONTO", "#16A34A")

    def _sleep_interruptible(self, seconds: float) -> bool:
        """Permite interromper o sleep instantaneamente caso o usuário pause ou pare."""
        steps = int(seconds / 0.1)
        for _ in range(steps):
            if self._stop_event.is_set():
                return False
            time.sleep(0.1)
        return not self._stop_event.is_set()

    def _update_live_ui(self, result: QuizSolutionResult) -> None:
        """Atualiza os cards do monitor com os dados retornados pela IA."""
        def update():
            self.lbl_last_answer.configure(
                text=f"Alternativa: {result.resposta}"
            )
            self.lbl_rationale.configure(
                text=result.rationale[:220] + ("..." if len(result.rationale) > 220 else "")
            )
            token_txt = f"{result.tokens_usados} Tokens" if not result.is_rag_cache else "0 Tokens (Cache RAG)"
            self.lbl_token_badge.configure(
                text=token_txt,
                text_color="#16A34A" if result.is_rag_cache else "#0284C7"
            )
        self.after(0, update)

    # =========================================================================
    # Utilitários de Interface e Hotkeys
    # =========================================================================
    def set_status(self, text: str, color: str = "#0284C7") -> None:
        self.after(0, lambda: self.status_badge.configure(text=f"● {text}", text_color=color))

    def log(self, message: str, level: str = "INFO") -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{timestamp}] [{level}] "
        formatted = f"{prefix}{message}\n"

        def append():
            self.log_box.insert("end", formatted)
            if self.config_manager.get("auto_scroll_logs", True):
                self.log_box.see("end")
        self.after(0, append)

    def clear_logs(self) -> None:
        self.log_box.delete("1.0", "end")

    def toggle_always_on_top(self) -> None:
        self.is_always_on_top = not self.is_always_on_top
        self.attributes("-topmost", self.is_always_on_top)
        self.config_manager.set("always_on_top", self.is_always_on_top)
        self.pin_btn.configure(
            text="📌 Fixar" if self.is_always_on_top else "📍 Solto",
            fg_color="#0284C7" if self.is_always_on_top else "#64748B"
        )
        self.log(f"Modo 'Always on Top': {'Ativado' if self.is_always_on_top else 'Desativado'}", "INFO")

    def toggle_stealth_mode(self) -> None:
        """Oculta ou restaura a janela instantaneamente (Alt + Q)."""
        if self._is_stealth_hidden:
            self.deiconify()
            self._is_stealth_hidden = False
        else:
            self.withdraw()
            self._is_stealth_hidden = True

    def _on_theme_changed(self, theme_name: str) -> None:
        ctk.set_appearance_mode(theme_name)
        self.config_manager.set("theme_mode", theme_name)
        self.log(f"Tema visual alterado para: {theme_name}", "INFO")

    def _register_hotkeys(self) -> None:
        if keyboard is None:
            return
        try:
            keyboard.add_hotkey("f8", self.toggle_autopilot)
            keyboard.add_hotkey("esc", self.emergency_stop)
            keyboard.add_hotkey("alt+q", self.toggle_stealth_mode)
        except Exception as e:
            print(f"[HOTKEY] Aviso ao registrar atalhos globais: {e}")

    def _on_close(self) -> None:
        self._stop_event.set()
        self._is_running = False
        self.destroy()


def main() -> None:
    setup_windows_dpi_awareness()
    app = MasteringStudyQuizApp()
    app.mainloop()


if __name__ == "__main__":
    main()
