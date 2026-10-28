"""
Motor de Automação RPA e Autopilot - Mastering Study Quiz
Gerencia o loop de resolução automática, cronômetros, gravação física no Cérebro,
suporte a modo Dry-Run (simulação) e emissão de bips de feedback sonoro.
"""

import time
import threading
from typing import Callable, Optional
from PIL import Image
import mss
import pyautogui

try:
    import winsound
except ImportError:
    winsound = None

from config_manager import ConfigManager
from ai_vision import AIVisionService, VisionAnalysisResult
from cerebro_manager import CerebroManager, QuestionSessionRecord
from metrics_tracker import MetricsTracker

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class AutomationEngine:
    """Motor de execução Autopilot com suporte a Dry-Run e sincronização contínua."""

    def __init__(
        self,
        config_manager: ConfigManager,
        ai_service: AIVisionService,
        cerebro_manager: CerebroManager,
        metrics_tracker: MetricsTracker,
        log_callback: Callable[[str, str], None],
        status_callback: Callable[[str], None],
        live_cerebro_callback: Optional[Callable[[QuestionSessionRecord], None]] = None,
        metrics_update_callback: Optional[Callable[[], None]] = None
    ):
        self.config_manager = config_manager
        self.ai_service = ai_service
        self.cerebro_manager = cerebro_manager
        self.metrics_tracker = metrics_tracker
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.live_cerebro_callback = live_cerebro_callback
        self.metrics_update_callback = metrics_update_callback

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
            self.log_callback("ERRO: Calibre a Área do Quiz no menu [⋮] antes de iniciar.", "ERROR")
            return False

        if not self.config_manager.get_current_api_key():
            self.log_callback("ERRO: Adicione uma chave Gemini em Configurações > Tokens.", "ERROR")
            return False

        if self._thread and self._thread.is_alive():
            if self._pause_event.is_set():
                self._pause_event.clear()
                self._set_active_status()
                self.log_callback("Autopilot retomado.", "INFO")
                return True
            return True

        self._stop_event.clear()
        self._pause_event.clear()
        self._is_active = True
        self.metrics_tracker.start_session()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._set_active_status()
        self.log_callback("Iniciando Autopilot com Motor Híbrido...", "SUCCESS")
        return True

    def _set_active_status(self) -> None:
        if self.config_manager.get("dry_run_mode", False):
            self.status_callback("SIMULAÇÃO DRY-RUN")
        else:
            self.status_callback("PRONTO")

    def pause(self) -> None:
        if self._is_active and not self._pause_event.is_set():
            self._pause_event.set()
            self.status_callback("PAUSADO")
            self.log_callback("Autopilot pausado.", "WARNING")

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
        self.log_callback("Autopilot interrompido pelo usuário.", "INFO")

    def _play_beep(self) -> None:
        """Toca um bip sutil caso o feedback sonoro esteja habilitado."""
        if self.config_manager.get("sound_feedback", True) and winsound:
            try:
                winsound.Beep(980, 120)
            except Exception:
                pass

    def _run_loop(self) -> None:
        question_idx = 0

        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.2)
                continue

            question_idx += 1
            self.metrics_tracker.start_question()
            if self.metrics_update_callback:
                self.metrics_update_callback()

            is_dry_run = self.config_manager.get("dry_run_mode", False)
            mode_tag = "[DRY-RUN]" if is_dry_run else "[AUTOPILOT]"
            self.log_callback(f"─── {mode_tag} Escaneando Questão #{question_idx} ───", "INFO")

            try:
                # 1. Captura da Tela via mss
                region = self.config_manager.get("quiz_region", {})
                x = int(region.get("x", 0))
                y = int(region.get("y", 0))
                w = int(region.get("width", 100))
                h = int(region.get("height", 100))

                self.status_callback("ANALISANDO")
                self.log_callback(f"Capturando região ({w}x{h} px)...", "INFO")
                screenshot_pil = self._capture_region(x, y, w, h)

                if self._stop_event.is_set():
                    break

                # 2. RAG Local & Consulta à IA
                rag_context = self.cerebro_manager.get_rag_context("análise inicial da tela")
                model_name = self.config_manager.get("model_name", "gemini-2.5-flash")
                self.log_callback(f"Consultando IA ({model_name})...", "INFO")

                result: VisionAnalysisResult = self.ai_service.analyze_quiz_image(screenshot_pil, rag_context)

                if self._stop_event.is_set():
                    break

                if not result.success:
                    self.log_callback(f"Falha na IA: {result.error_message}", "ERROR")
                    self._interruptible_sleep(3.5)
                    continue

                # 3. Recorte de Elemento Visual
                recorte: Optional[Image.Image] = None
                if result.possui_elemento_visual:
                    bb = result.bounding_box_elemento
                    ymin, xmin, ymax, xmax = bb.get("ymin", 0), bb.get("xmin", 0), bb.get("ymax", 0), bb.get("xmax", 0)
                    if ymax > ymin and xmax > xmin:
                        crop_box = (int(xmin * w), int(ymin * h), int(xmax * w), int(ymax * h))
                        recorte = screenshot_pil.crop(crop_box)
                    else:
                        recorte = screenshot_pil.copy()
                else:
                    recorte = screenshot_pil.copy()

                # 4. Cálculo de Coordenadas Globais do Monitor
                coord_norm = result.coordenadas_resposta
                click_x = x + int(coord_norm["x_norm"] * w)
                click_y = y + int(coord_norm["y_norm"] * h)

                # 5. Persistência Física no Cérebro (Pastas, Rationale, Mídias)
                session_record = self.cerebro_manager.record_question_session(
                    pergunta=result.pergunta_extraida,
                    resposta=result.alternativa_correta,
                    rationale=result.rationale,
                    confianca=result.confianca,
                    possui_elemento_visual=result.possui_elemento_visual,
                    categoria=result.categoria_imagem,
                    contexto_imagem=result.contexto_imagem,
                    imagem_recorte=recorte,
                    coordenadas_clique={"x": click_x, "y": click_y},
                    prompt_enviado=result.prompt_enviado,
                    rag_contexto=rag_context,
                    modelo=model_name,
                    latencia_ms=result.latencia_ms,
                    tokens_usados=result.tokens_usados
                )

                # 6. Atualização de Métricas
                self.metrics_tracker.finish_question(
                    question_idx=question_idx,
                    answer=result.alternativa_correta,
                    has_visual=result.possui_elemento_visual,
                    category=result.categoria_imagem,
                    tokens=result.tokens_usados,
                    latency_ms=result.latencia_ms
                )

                # Atualiza tela do Cérebro e Métricas em tempo real
                if self.live_cerebro_callback:
                    self.live_cerebro_callback(session_record)
                if self.metrics_update_callback:
                    self.metrics_update_callback()

                self.log_callback(f"Cérebro Atualizado: [{result.categoria_imagem}] {result.pergunta_extraida[:50]}...", "SUCCESS")
                self.log_callback(f"Resposta: {result.alternativa_correta} (Latência: {result.latencia_ms}ms | Tokens: {result.tokens_usados})", "SUCCESS")

                # Feedback Sonoro
                self._play_beep()

                # 7. Ação de Clique (ou Simulação Dry-Run)
                if is_dry_run:
                    self.status_callback("SIMULAÇÃO DRY-RUN")
                    self.log_callback(f"[DRY-RUN] Simulação ativa: Resposta detectada mas clique ignorado em ({click_x}, {click_y}).", "WARNING")
                else:
                    if self.config_manager.get("auto_apply", True):
                        self.status_callback("RESPONDENDO")
                        self.log_callback(f"Clicando na alternativa em ({click_x}, {click_y})...", "INFO")
                        if self.config_manager.get("smooth_mouse", True):
                            pyautogui.moveTo(click_x, click_y, duration=0.32, tween=pyautogui.easeOutQuad)
                        else:
                            pyautogui.moveTo(click_x, click_y)
                        pyautogui.click()

                # Delay pós-resposta
                delay = float(self.config_manager.get("action_delay", 2.0))
                if not self._interruptible_sleep(delay):
                    break

                # 8. Avanço Automático para a Próxima Pergunta
                auto_adv = self.config_manager.get("auto_advance", True)
                next_btn = self.config_manager.get("next_button", {})

                if not is_dry_run and auto_adv and next_btn.get("configured", False):
                    nx = int(next_btn["x"])
                    ny = int(next_btn["y"])
                    self.log_callback(f"Avançando no botão Próximo ({nx}, {ny})...", "INFO")
                    pyautogui.moveTo(nx, ny, duration=0.22, tween=pyautogui.easeOutQuad)
                    pyautogui.click()

                    trans_delay = float(self.config_manager.get("transition_delay", 1.5))
                    self.log_callback(f"Aguardando carregamento da nova questão ({trans_delay:.1f}s)...", "INFO")
                    if not self._interruptible_sleep(trans_delay):
                        break
                else:
                    if not self._interruptible_sleep(2.0):
                        break

            except pyautogui.FailSafeException:
                self.log_callback("PARADA DE EMERGÊNCIA: Mouse no canto da tela acionou Failsafe!", "ERROR")
                self.stop()
                break
            except Exception as e:
                self.log_callback(f"Erro no loop de automação: {str(e)}", "ERROR")
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
