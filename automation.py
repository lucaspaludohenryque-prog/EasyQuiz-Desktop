"""
Módulo de Automação de Interface (RPA), Captura de Tela e Controle de Mouse
Mastering Study Quiz - Etapa 2
Fornece:
1. Ferramenta de Recorte Transparente em Tela Cheia (Bounding Box Vermelho).
2. Mapeador de Coordenadas do Botão Próximo.
3. Captura rápida de região de tela via mss em memória (RGB PIL.Image).
4. Controle suave de mouse com PyAutoGUI e Tweening.
5. Auto-digitação humanizada para questões discursivas.
"""

import time
import random
import threading
import tkinter as tk
from typing import Callable, Optional, Tuple, Dict, Any
from PIL import Image
import mss
import pyautogui

# Configurações de segurança do PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class TransparentCropOverlay:
    """
    Janela em tela cheia transparente para seleção de área de corte.
    O usuário clica e arrasta para desenhar um retângulo vermelho (bounding box).
    Ao soltar, fecha a janela e retorna (x, y, largura, altura).
    """

    def __init__(self, master: Optional[tk.Misc], callback: Callable[[int, int, int, int], None]):
        self.master = master
        self.callback = callback
        self.start_x: Optional[int] = None
        self.start_y: Optional[int] = None
        self.rect_id: Optional[int] = None
        self.text_id: Optional[int] = None

        if master is not None:
            self.top = tk.Toplevel(master)
        else:
            self.top = tk.Tk()

        # Configurações da Janela em Tela Cheia Translúcida
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.attributes("-alpha", 0.30)
        self.top.config(cursor="cross")

        # Canvas escuro para contraste nítido
        self.canvas = tk.Canvas(self.top, bg="#0A0A0A", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        screen_w = self.top.winfo_screenwidth()
        screen_h = self.top.winfo_screenheight()

        # Banner de instrução no topo
        self.canvas.create_rectangle(
            screen_w // 2 - 320, 25, screen_w // 2 + 320, 75,
            fill="#141414", outline="#FF0033", width=2
        )
        self.canvas.create_text(
            screen_w // 2, 50,
            text="CLIQUE E ARRASTE O MOUSE PARA DEFINIR A ÁREA DO QUIZ  |  [ESC] Cancelar",
            fill="#FFFFFF",
            font=("Segoe UI", 12, "bold")
        )

        # Bindings de mouse e teclado
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.top.bind("<Escape>", lambda e: self._close())

    def _on_mouse_down(self, event: tk.Event) -> None:
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        if self.text_id:
            self.canvas.delete(self.text_id)

        # Retângulo com contorno vermelho brilhante (#FF0033)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#FF0033", width=3, fill="#FF0033", stipple="gray25"
        )

    def _on_mouse_drag(self, event: tk.Event) -> None:
        if self.start_x is None or self.start_y is None or self.rect_id is None:
            return

        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

        width = abs(cur_x - self.start_x)
        height = abs(cur_y - self.start_y)
        label_text = f"{width} x {height} px"

        label_x = max(self.start_x, cur_x) + 5
        label_y = max(self.start_y, cur_y) + 20

        if self.text_id:
            self.canvas.coords(self.text_id, label_x, label_y)
            self.canvas.itemconfig(self.text_id, text=label_text)
        else:
            self.text_id = self.canvas.create_text(
                label_x, label_y,
                text=label_text, fill="#FF0033", font=("Segoe UI", 11, "bold"), anchor="w"
            )

    def _on_mouse_up(self, event: tk.Event) -> None:
        if self.start_x is None or self.start_y is None:
            self._close()
            return

        end_x, end_y = event.x, event.y
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        width = x2 - x1
        height = y2 - y1

        self._close()

        # Validação mínima de área
        if width > 30 and height > 30:
            print(f"[RPA] Área de Quiz selecionada: X={x1}, Y={y1}, Largura={width}, Altura={height}")
            self.callback(x1, y1, width, height)
        else:
            print("[RPA] Seleção descartada (área muito pequena).")

    def _close(self) -> None:
        try:
            self.top.destroy()
        except Exception:
            pass


class NextButtonTargetOverlay:
    """
    Overlay interativo para mapear com precisão a coordenada (X, Y) do botão Próximo.
    """

    def __init__(self, master: Optional[tk.Misc], callback: Callable[[int, int], None]):
        self.master = master
        self.callback = callback

        if master is not None:
            self.top = tk.Toplevel(master)
        else:
            self.top = tk.Tk()

        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.attributes("-alpha", 0.30)
        self.top.config(cursor="crosshair")

        self.canvas = tk.Canvas(self.top, bg="#0A0A0A", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        screen_w = self.top.winfo_screenwidth()

        self.canvas.create_rectangle(
            screen_w // 2 - 320, 25, screen_w // 2 + 320, 75,
            fill="#141414", outline="#00E5FF", width=2
        )
        self.canvas.create_text(
            screen_w // 2, 50,
            text="CLIQUE EXATAMENTE EM CIMA DO BOTÃO 'PRÓXIMO / VERIFICAR'  |  [ESC] Cancelar",
            fill="#00E5FF",
            font=("Segoe UI", 12, "bold")
        )

        self.canvas.bind("<Button-1>", self._on_click)
        self.top.bind("<Escape>", lambda e: self._close())

    def _on_click(self, event: tk.Event) -> None:
        x = event.x_root
        y = event.y_root
        self._close()
        print(f"[RPA] Botão Próximo mapeado na coordenada: X={x}, Y={y}")
        self.callback(x, y)

    def _close(self) -> None:
        try:
            self.top.destroy()
        except Exception:
            pass


# =============================================================================
# Funções Principais de Captura e Movimento
# =============================================================================

def open_crop_selector(master: Optional[tk.Misc], callback: Callable[[int, int, int, int], None]) -> None:
    """Abre a ferramenta de seleção transparente de área da tela."""
    TransparentCropOverlay(master, callback)


def open_next_button_mapper(master: Optional[tk.Misc], callback: Callable[[int, int], None]) -> None:
    """Abre o mapeador visual do botão Próximo."""
    NextButtonTargetOverlay(master, callback)


def capture_screen_region(x: int, y: int, width: int, height: int) -> Image.Image:
    """
    Captura instantânea da região demarcada da tela usando mss (alta performance).
    Retorna objeto PIL.Image.Image RGB em memória.
    """
    with mss.mss() as sct:
        monitor = {
            "top": int(y),
            "left": int(x),
            "width": int(width),
            "height": int(height)
        }
        sct_img = sct.grab(monitor)
        # Converte BGRA de mss diretamente para RGB do Pillow
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")


def smooth_click(
    x: int,
    y: int,
    duration: float = 0.28,
    clicks: int = 1,
    button: str = "left"
) -> None:
    """
    Move o cursor até as coordenadas absolutas (x, y) com curva de suavização
    (easeOutQuad) e executa o clique.
    """
    pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeOutQuad)
    pyautogui.click(button=button, clicks=clicks)


def click_next_button(next_x: int, next_y: int, delay_after: float = 1.5) -> None:
    """
    Clica no botão Próximo/Verificar com movimento suave e aguarda o carregamento.
    """
    pyautogui.moveTo(next_x, next_y, duration=0.22, tween=pyautogui.easeOutQuad)
    pyautogui.click()
    if delay_after > 0:
        time.sleep(delay_after)


def type_humanized(text: str, min_delay_ms: int = 25, max_delay_ms: int = 75) -> None:
    """
    Digita um texto simulando a velocidade e cadência humana
    com micro-variações em milissegundos entre cada caractere.
    """
    for char in text:
        pyautogui.write(char)
        sleep_sec = random.uniform(min_delay_ms / 1000.0, max_delay_ms / 1000.0)
        time.sleep(sleep_sec)
