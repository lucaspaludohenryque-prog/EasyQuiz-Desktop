"""
Módulo de Automação de Interface (RPA) - Mastering Study Quiz
Captura a tela com mss, consulta a IA, recorta elementos visuais,
registra no Cérebro em tempo real e comanda o mouse com PyAutoGUI.
"""

import time
import threading
from typing import Callable, Optional
from PIL import Image
import mss
import pyautogui

from config_manager import ConfigManager
from ai_vision import AIVisionService, VisionAnalysisResult
from cerebro_manager import CerebroManager, CerebroItem

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class AutomationEngine:
    """Motor de execução do quiz com sincronização contínua com a interface gráfica."""

    def __init__(
        self,
        config_manager: ConfigManager,
        ai_service: AIVisionService,
        cerebro_manager: CerebroManager,
        log_callback: Callable[[str, str], None],
        status_callback: Callable[[str], None],
        live_cerebro_callback: Optional[Callable[[CerebroItem], None]] = None
    ):
        self.config_manager = config_manager
        self.ai_service = ai_service
        self.cerebro_manager = cerebro_manager
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.live_cerebro_callback = live_cerebro_callback

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
        region = self.config_manager.get("quiz_region", {})
        if not region.get("configured", False):
            self.log_callback("ERRO: Delimite a Área do Quiz antes de iniciar.", "ERROR")
            return False

        if not self.config_manager.get("api_key"):
            self.log_callback("ERRO: Configure sua API Key no painel Configurações.", "ERROR")
            return False

        if self._thread and self._thread.is_alive():
            if self._pause_event.is_set():
                self._pause_event.clear()
                self.status_callback("EXECUTANDO")
                self.log_callback("Automação retomada.", "INFO")
                return True
            return True

        self._stop_event.clear()
        self._pause_event.clear()
        self._is_active = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.status_callback("EXECUTANDO")
        self.log_callback("Iniciando varredura automatizada com IA Multimodal...", "SUCCESS")
        return True

    def pause(self) -> None:
        if self._is_active and not self._pause_event.is_set():
            self._pause_event.set()
            self.status_callback("PAUSADO")
            self.log_callback("Automação pausada temporariamente.", "WARNING")

    def toggle_play_pause(self) -> None:
        if not self._is_active:
            self.start()
        elif self.is_paused:
            self.start()
        else:
            self.pause()

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.clear()
        self._is_active = False
        self.status_callback("PARADO")
        self.log_callback("Automação finalizada.", "INFO")

    def _run_loop(self) -> None:
        question_idx = 0

        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.2)
                continue

            question_idx += 1
            self.log_callback(f"─── Escaneando Questão #{question_idx} ───", "INFO")

            try:
                # 1. Captura com mss
                region = self.config_manager.get("quiz_region", {})
                x = int(region.get("x", 0))
                y = int(region.get("y", 0))
                w = int(region.get("width", 100))
                h = int(region.get("height", 100))

                self.status_callback("ESCANEANDO")
                self.log_callback(f"Capturando tela ({w}x{h} px)...", "INFO")
                screenshot_pil = self._capture_region(x, y, w, h)

                if self._stop_event.is_set():
                    break

                # 2. Consulta à IA Multimodal
                self.status_callback("ANALISANDO")
                prov = self.config_manager.get("api_provider", "gemini").upper()
                mod = self.config_manager.get("model_name", "")
                self.log_callback(f"Enviando para IA Multimodal [{prov}: {mod}]...", "INFO")

                result: VisionAnalysisResult = self.ai_service.analyze_quiz_image(screenshot_pil)

                if self._stop_event.is_set():
                    break

                if not result.success:
                    self.log_callback(f"Falha na IA: {result.error_message}", "ERROR")
                    self._interruptible_sleep(3.5)
                    continue

                # 3. Recorte e Registro no Cérebro
                recorte_elemento: Optional[Image.Image] = None
                if result.possui_elemento_visual:
                    bbox = result.bounding_box_elemento
                    ymin, xmin, ymax, xmax = bbox.get("ymin", 0), bbox.get("xmin", 0), bbox.get("ymax", 0), bbox.get("xmax", 0)
                    if ymax > ymin and xmax > xmin:
                        crop_box = (
                            int(xmin * w),
                            int(ymin * h),
                            int(xmax * w),
                            int(ymax * h)
                        )
                        recorte_elemento = screenshot_pil.crop(crop_box)
                    else:
                        recorte_elemento = screenshot_pil.copy()
                else:
                    # Salva uma miniatura geral se for texto puro para compor o histórico
                    recorte_elemento = screenshot_pil.copy()

                # 4. Cálculo das Coordenadas Finais da Resposta
                coord_norm = result.coordenadas_resposta
                click_x = x + int(coord_norm["x_norm"] * w)
                click_y = y + int(coord_norm["y_norm"] * h)

                # 5. Persistência no Cérebro
                cerebro_item = self.cerebro_manager.add_item(
                    pergunta=result.pergunta_extraida,
                    resposta=result.alternativa_correta,
                    confianca=result.confianca,
                    possui_elemento_visual=result.possui_elemento_visual,
                    categoria=result.categoria_imagem,
                    contexto=result.contexto_imagem,
                    imagem_recorte=recorte_elemento,
                    coordenadas_clique={"x": click_x, "y": click_y}
                )

                # Atualização imediata do painel "Cérebro em Tempo Real" na GUI
                if self.live_cerebro_callback:
                    self.live_cerebro_callback(cerebro_item)

                categoria_badge = f"[{result.categoria_imagem.upper()}]"
                self.log_callback(f"Cérebro Registrado: {categoria_badge} {result.pergunta_extraida[:65]}...", "SUCCESS")
                self.log_callback(f"Resposta Correta: {result.alternativa_correta}", "SUCCESS")

                # 6. Ação do Mouse (Clique na Resposta)
                self.status_callback("CLICANDO")
                self.log_callback(f"Clicando na alternativa em ({click_x}, {click_y})...", "INFO")
                if self.config_manager.get("smooth_mouse", True):
                    pyautogui.moveTo(click_x, click_y, duration=0.35, tween=pyautogui.easeOutQuad)
                else:
                    pyautogui.moveTo(click_x, click_y)

                pyautogui.click()

                # 7. Delay entre resposta e próximo
                delay = float(self.config_manager.get("action_delay", 2.0))
                self.log_callback(f"Aguardando delay pós-resposta ({delay:.1f}s)...", "INFO")
                if not self._interruptible_sleep(delay):
                    break

                # 8. Avanço Automático para a Próxima Pergunta
                auto_adv = self.config_manager.get("auto_advance", True)
                next_btn = self.config_manager.get("next_button", {})

                if auto_adv and next_btn.get("configured", False):
                    nx = int(next_btn["x"])
                    ny = int(next_btn["y"])
                    self.log_callback(f"Avançando questão no botão ({nx}, {ny})...", "INFO")
                    pyautogui.moveTo(nx, ny, duration=0.25, tween=pyautogui.easeOutQuad)
                    pyautogui.click()

                    trans_delay = float(self.config_manager.get("transition_delay", 1.5))
                    self.log_callback(f"Aguardando carregamento da nova tela ({trans_delay:.1f}s)...", "INFO")
                    if not self._interruptible_sleep(trans_delay):
                        break
                else:
                    self.log_callback("Botão Próximo não definido. Aguardando novo ciclo...", "WARNING")
                    if not self._interruptible_sleep(2.5):
                        break

            except pyautogui.FailSafeException:
                self.log_callback("PARADA DE EMERGÊNCIA: Mouse no canto da tela!", "ERROR")
                self.stop()
                break
            except Exception as e:
                self.log_callback(f"Erro no ciclo: {str(e)}", "ERROR")
                if not self._interruptible_sleep(3.0):
                    break

        self._is_active = False
        self.status_callback("PARADO")

    def _capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        with mss.mss() as sct:
            mon = {"top": y, "left": x, "width": width, "height": height}
            sct_img = sct.grab(mon)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    def _interruptible_sleep(self, seconds: float) -> bool:
        steps = int(seconds / 0.1)
        for _ in range(steps):
            if self._stop_event.is_set():
                return False
            time.sleep(0.1)
        rem = seconds - (steps * 0.1)
        if rem > 0:
            time.sleep(rem)
        return not self._stop_event.is_set()
