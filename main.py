"""
Ponto de Entrada Principal - Mastering Study Quiz
Inicializa o reconhecimento de DPI no Windows, instancia os serviços locais
e dispara a interface gráfica no formato vertical dockable.
"""

import sys
import ctypes

from config_manager import ConfigManager
from ai_vision import AIVisionService
from cerebro_manager import CerebroManager
from metrics_tracker import MetricsTracker
from gui import MasteringStudyQuizGUI


def setup_windows_dpi_awareness() -> None:
    """Configura o reconhecimento de DPI do Windows para alinhamento sub-pixel no RPA."""
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
    """Inicialização dos serviços e do loop principal de interface."""
    setup_windows_dpi_awareness()

    # Gerenciador de configurações locais (config.json)
    config_mgr = ConfigManager("config.json")

    # Gerenciador de pastas físicas e sessões (Cerebro_Dados/)
    cerebro_mgr = CerebroManager()

    # Rastreador de cronômetro, tokens e métricas
    metrics_trk = MetricsTracker()

    # Serviço de IA Multimodal com suporte a rotação de chaves
    ai_service = AIVisionService(config_manager=config_mgr)

    # Inicialização da Interface Gráfica Vertical Dockable
    app = MasteringStudyQuizGUI(
        config_manager=config_mgr,
        ai_service=ai_service,
        cerebro_manager=cerebro_mgr,
        metrics_tracker=metrics_trk
    )
    app.mainloop()


if __name__ == "__main__":
    main()
