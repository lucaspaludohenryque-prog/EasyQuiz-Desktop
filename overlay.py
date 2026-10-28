"""
Módulo de Sobreposição de Calibração Visual (Sniper Overlay)
Permite a demarcação interativa da área do quiz e captura de coordenadas de botões na tela.
"""

import tkinter as tk
from typing import Callable, Optional, Tuple


class ScreenAreaSelector:
    """Sobreposição translúcida em tela cheia para seleção de retângulo por arrasto."""

    def __init__(self, master: tk.Misc, callback: Callable[[int, int, int, int], None]):
        self.master = master
        self.callback = callback
        self.start_x: Optional[int] = None
        self.start_y: Optional[int] = None
        self.rect_id: Optional[int] = None
        self.text_id: Optional[int] = None

        self.top = tk.Toplevel(master)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.attributes("-alpha", 0.35)
        self.top.config(cursor="cross")

        # Canvas para desenho do retângulo
        self.canvas = tk.Canvas(self.top, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Instruções na tela
        self.info_label = self.canvas.create_text(
            self.top.winfo_screenwidth() // 2,
            50,
            text="CLIQUE E ARRASTE O MOUSE PARA DEFINIR A ÁREA DO QUIZ  |  Pressione [ESC] para Cancelar",
            fill="#FFFFFF",
            font=("Segoe UI", 16, "bold")
        )

        # Eventos do mouse e teclado
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.top.bind("<Escape>", lambda e: self._close())

    def _on_press(self, event: tk.Event) -> None:
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        if self.text_id:
            self.canvas.delete(self.text_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#00E5FF", width=3, fill="#00E5FF", stipple="gray25"
        )

    def _on_drag(self, event: tk.Event) -> None:
        if self.start_x is None or self.start_y is None or self.rect_id is None:
            return
        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

        width = abs(cur_x - self.start_x)
        height = abs(cur_y - self.start_y)
        label_text = f"{width} x {height} px"

        if self.text_id:
            self.canvas.coords(self.text_id, max(self.start_x, cur_x), max(self.start_y, cur_y) + 20)
            self.canvas.itemconfig(self.text_id, text=label_text)
        else:
            self.text_id = self.canvas.create_text(
                max(self.start_x, cur_x), max(self.start_y, cur_y) + 20,
                text=label_text, fill="#00E5FF", font=("Segoe UI", 11, "bold")
            )

    def _on_release(self, event: tk.Event) -> None:
        if self.start_x is None or self.start_y is None:
            self._close()
            return

        end_x, end_y = event.x, event.y
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        w = x2 - x1
        h = y2 - y1

        self._close()
        if w > 20 and h > 20:
            self.callback(x1, y1, w, h)

    def _close(self) -> None:
        self.top.destroy()


class PointSelector:
    """Sobreposição para captura de coordenada única (X, Y) com clique do mouse."""

    def __init__(self, master: tk.Misc, callback: Callable[[int, int], None], prompt: str = "Clique no Botão de Avançar"):
        self.master = master
        self.callback = callback

        self.top = tk.Toplevel(master)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.attributes("-alpha", 0.35)
        self.top.config(cursor="target")

        self.canvas = tk.Canvas(self.top, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.create_text(
            self.top.winfo_screenwidth() // 2,
            50,
            text=f"🎯 {prompt.upper()}  |  Pressione [ESC] para Cancelar",
            fill="#00FF66",
            font=("Segoe UI", 16, "bold")
        )

        self.canvas.bind("<Button-1>", self._on_click)
        self.top.bind("<Escape>", lambda e: self._close())

    def _on_click(self, event: tk.Event) -> None:
        # Usa coordenadas absolutas da tela
        x = event.x_root
        y = event.y_root
        self._close()
        self.callback(x, y)

    def _close(self) -> None:
        self.top.destroy()
