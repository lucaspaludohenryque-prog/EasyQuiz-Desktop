"""
Ponto de Entrada Principal - EasyQuiz Desktop
Inicializa a compatibilidade de DPI no Windows, instancia serviços e inicializa a interface gráfica.
"""

import sys
import os
import ctypes

from config_manager import ConfigManager
from ai_service import AIService
from gui import EasyQuizGUI


def setup_windows_dpi_awareness() -> None:
    """Configura o reconhecimento de DPI do Windows para garantir precisão nas coordenadas do RPA."""
    if sys.platform.startswith("win"):
        try:
            # PROCESS_PER_MONITOR_DPI_AWARE (Windows 8.1+)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                # Fallback para versões legadas (Windows Vista/7/8)
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def main() -> None:
    """Função principal de inicialização da aplicação."""
    setup_windows_dpi_awareness()

    # Inicializa persistência de configurações
    config_mgr = ConfigManager("config.json")

    # Inicializa serviço de IA com os dados persistidos
    ai_service = AIService(
        provider=config_mgr.get("api_provider", "gemini"),
        api_key=config_mgr.get("api_key", ""),
        model_name=config_mgr.get("model_name", "gemini-2.5-flash")
    )

    # Inicia a Interface Gráfica
    app = EasyQuizGUI(config_manager=config_mgr, ai_service=ai_service)
    app.mainloop()


if __name__ == "__main__":
    main()
