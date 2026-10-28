"""
Ponto de Entrada Principal - Mastering Study Quiz
Inicializa compatibilidade de DPI no Windows, instancia os serviços locais do Cérebro
e inicializa a interface gráfica em modo claro padrão.
"""

import sys
import ctypes

from config_manager import ConfigManager
from ai_vision import AIVisionService
from cerebro_manager import CerebroManager
from gui import MasteringStudyQuizGUI


def setup_windows_dpi_awareness() -> None:
    """Configura o reconhecimento de DPI do Windows para garantir precisão nas coordenadas do RPA."""
    if sys.platform.startswith("win"):
        try:
            # PROCESS_PER_MONITOR_DPI_AWARE
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def main() -> None:
    """Função principal de inicialização da aplicação."""
    setup_windows_dpi_awareness()

    # Gerenciador de configurações locais (config.json)
    config_mgr = ConfigManager("config.json")

    # Gerenciador do Cérebro (Cerebro_Dados/ e database_cerebro.json)
    cerebro_mgr = CerebroManager()

    # Serviço de IA Multimodal
    ai_service = AIVisionService(
        provider=config_mgr.get("api_provider", "gemini"),
        api_key=config_mgr.get("api_key", ""),
        model_name=config_mgr.get("model_name", "gemini-2.5-flash")
    )

    # Inicializa e executa a interface gráfica
    app = MasteringStudyQuizGUI(
        config_manager=config_mgr,
        ai_service=ai_service,
        cerebro_manager=cerebro_mgr
    )
    app.mainloop()


if __name__ == "__main__":
    main()
