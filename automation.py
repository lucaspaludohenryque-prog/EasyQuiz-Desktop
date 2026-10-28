"""
Módulo de Automação de Interface (RPA) - EasyQuiz Desktop
Controla a captura em tempo real com mss, resolução com IA e automação do mouse via PyAutoGUI.
"""

import time
import threading
from typing import Callable, Optional
from PIL import Image
import mss
import pyautogui

from config_manager import ConfigManager
from ai_service import AIService, QuizSolution

# Configura segurança padrão do PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class AutomationEngine:
    """Motor de execução em thread separada com suporte a pausa, retomada e parada emergencial."""

    def __init__(
        self,
        config_manager: ConfigManager,
        ai_service: AIService,
        log_callback: Callable[[str, str], None],
        status_callback: Callable[[str], None]
    ):
        self.config_manager = config_manager
        self.ai_service = ai_service
        self.log_callback = log_callback
        self.status_callback = status_callback

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._is_active = False

    @property
    def is_running(self) -> bool:
        return self._is_active and not self._pause_event.is_set()

    @property
    def is_paused(self) -> bool:
        return self._is_active and self._pause_event.is_set()

    def start(self) -> bool:
        """Inicia ou retoma o loop de automação."""
        quiz_region = self.config_manager.get("quiz_region", {})
        if not quiz_region.get("configured", False):
            self.log_callback("ERRO: Defina a Área do Quiz antes de iniciar a automação.", "ERROR")
            return False

        if not self.config_manager.get("api_key"):
            self.log_callback("ERRO: Insira e salve sua API Key antes de iniciar.", "ERROR")
            return False

        if self._thread and self._thread.is_alive():
            if self._pause_event.is_set():
                self._pause_event.clear()
                self.status_callback("EXECUTANDO")
                self.log_callback("Automação retomada pelo usuário.", "INFO")
                return True
            return True

        self._stop_event.clear()
        self._pause_event.clear()
        self._is_active = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.status_callback("EXECUTANDO")
        self.log_callback("Iniciando loop de automação inteligente...", "SUCCESS")
        return True

    def pause(self) -> None:
        """Pausa a automação mantendo a thread em espera."""
        if self._is_active and not self._pause_event.is_set():
            self._pause_event.set()
            self.status_callback("PAUSADO")
            self.log_callback("Automação pausada temporariamente.", "WARNING")

    def toggle_play_pause(self) -> None:
        """Alterna entre executar e pausar (útil para hotkeys como F8)."""
        if not self._is_active:
            self.start()
        elif self.is_paused:
            self.start()
        else:
            self.pause()

    def stop(self) -> None:
        """Interrompe a thread de automação imediatamente."""
        self._stop_event.set()
        self._pause_event.clear()
        self._is_active = False
        self.status_callback("PARADO")
        self.log_callback("Automação encerrada com sucesso.", "INFO")

    def _run_loop(self) -> None:
        """Ciclo principal de execução executado na worker thread."""
        question_counter = 0

        while not self._stop_event.is_set():
            # Tratamento de pausa
            if self._pause_event.is_set():
                time.sleep(0.3)
                continue

            question_counter += 1
            self.log_callback(f"--- Processando Questão #{question_counter} ---", "INFO")

            try:
                # 1. Captura da região configurada
                region = self.config_manager.get("quiz_region", {})
                x = int(region.get("x", 0))
                y = int(region.get("y", 0))
                w = int(region.get("width", 100))
                h = int(region.get("height", 100))

                self.log_callback(f"Capturando região da tela ({w}x{h} px)...", "INFO")
                screenshot_pil = self._capture_screen_region(x, y, w, h)

                if self._stop_event.is_set():
                    break

                # 2. Consulta à Inteligência Artificial
                provider = self.config_manager.get("api_provider", "gemini").upper()
                model = self.config_manager.get("model_name", "")
                self.log_callback(f"Consultando IA via {provider} ({model})...", "INFO")

                solution: QuizSolution = self.ai_service.solve_quiz(screenshot_pil)

                if self._stop_event.is_set():
                    break

                if not solution.success:
                    self.log_callback(f"Falha na IA: {solution.error_message}", "ERROR")
                    self.log_callback("Aguardando 4 segundos para nova tentativa...", "WARNING")
                    self._interruptible_sleep(4.0)
                    continue

                # 3. Processamento das coordenadas
                box = solution.target_box_normalized
                center_x_norm = (box.get("xmin", 0.5) + box.get("xmax", 0.5)) / 2.0
                center_y_norm = (box.get("ymin", 0.5) + box.get("ymax", 0.5)) / 2.0

                click_x = x + int(center_x_norm * w)
                click_y = y + int(center_y_norm * h)

                conf_percent = solution.confidence * 100
                self.log_callback(f"Questão: '{solution.question}'", "INFO")
                self.log_callback(f"Resposta IA: '{solution.chosen_answer}' (Confiança: {conf_percent:.1f}%)", "SUCCESS")
                self.log_callback(f"Coordenadas calculadas: ({click_x}, {click_y})", "INFO")

                # 4. Movimento e Clique na Resposta
                if self.config_manager.get("smooth_mouse", True):
                    pyautogui.moveTo(click_x, click_y, duration=0.35, tween=pyautogui.easeOutQuad)
                else:
                    pyautogui.moveTo(click_x, click_y)

                pyautogui.click()
                self.log_callback("Clique na resposta realizado.", "SUCCESS")

                # 5. Delay configurado entre resposta e avançar
                action_delay = float(self.config_manager.get("action_delay", 2.0))
                self.log_callback(f"Aguardando delay pós-resposta ({action_delay:.1f}s)...", "INFO")
                if not self._interruptible_sleep(action_delay):
                    break

                # 6. Avanço Automático para a Próxima Pergunta (se configurado)
                auto_advance = self.config_manager.get("auto_advance", True)
                next_btn = self.config_manager.get("next_button", {})

                if auto_advance and next_btn.get("configured", False):
                    next_x = int(next_btn.get("x", 0))
                    next_y = int(next_btn.get("y", 0))

                    self.log_callback(f"Clicando no botão de avançar em ({next_x}, {next_y})...", "INFO")
                    if self.config_manager.get("smooth_mouse", True):
                        pyautogui.moveTo(next_x, next_y, duration=0.25, tween=pyautogui.easeOutQuad)
                    else:
                        pyautogui.moveTo(next_x, next_y)
                    pyautogui.click()

                    # Tempo para a página web carregar a próxima pergunta
                    trans_delay = float(self.config_manager.get("transition_delay", 1.5))
                    self.log_callback(f"Aguardando carregamento da nova questão ({trans_delay:.1f}s)...", "INFO")
                    if not self._interruptible_sleep(trans_delay):
                        break
                else:
                    self.log_callback("Avanço automático desativado ou botão próximo não definido.", "WARNING")
                    # Pequena pausa antes de checar a tela novamente
                    if not self._interruptible_sleep(2.0):
                        break

            except pyautogui.FailSafeException:
                self.log_callback("PARADA DE EMERGÊNCIA: Mouse movido para o canto da tela!", "ERROR")
                self.stop()
                break
            except Exception as e:
                self.log_callback(f"Erro inesperado no loop: {str(e)}", "ERROR")
                if not self._interruptible_sleep(3.0):
                    break

        self._is_active = False
        self.status_callback("PARADO")

    def _capture_screen_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """Captura ultra-rápida de um quadrante da tela utilizando a biblioteca mss."""
        with mss.mss() as sct:
            monitor = {"top": y, "left": x, "width": width, "height": height}
            sct_img = sct.grab(monitor)
            # Converte BGRA de mss para RGB PIL Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img

    def _interruptible_sleep(self, seconds: float) -> bool:
        """Pausa fracionada que responde imediatamente ao evento de parada."""
        steps = int(seconds / 0.1)
        for _ in range(steps):
            if self._stop_event.is_set():
                return False
            time.sleep(0.1)
        # Fração restante
        remainder = seconds - (steps * 0.1)
        if remainder > 0:
            time.sleep(remainder)
        return not self._stop_event.is_set()
