"""
Módulo de Gerenciamento de Configurações - EasyQuiz Desktop
Responsável pela persistência e recuperação de configurações locais do aplicativo em JSON.
"""

import json
import os
from typing import Dict, Any, Optional

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_provider": "gemini",
    "api_key": "",
    "model_name": "gemini-2.5-flash",
    "quiz_region": {
        "x": 0,
        "y": 0,
        "width": 0,
        "height": 0,
        "configured": False
    },
    "next_button": {
        "x": 0,
        "y": 0,
        "configured": False
    },
    "action_delay": 2.5,
    "transition_delay": 1.5,
    "auto_advance": True,
    "smooth_mouse": True
}


class ConfigManager:
    """Gerencia a leitura e gravação das configurações no arquivo config.json."""

    def __init__(self, config_filename: str = "config.json"):
        # Garante que o config.json fique sempre na pasta do executável/script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(base_dir, config_filename)
        self.config_data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """Carrega as configurações do arquivo JSON ou inicializa com valores padrão."""
        if not os.path.exists(self.config_path):
            return self._save_defaults()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Mescla chaves ausentes com os defaults para garantir compatibilidade
                merged = DEFAULT_CONFIG.copy()
                for key, val in loaded.items():
                    if isinstance(val, dict) and key in merged and isinstance(merged[key], dict):
                        merged[key].update(val)
                    else:
                        merged[key] = val
                return merged
        except Exception:
            # Em caso de corrupção do arquivo, restaura defaults
            return self._save_defaults()

    def _save_defaults(self) -> Dict[str, Any]:
        """Cria e grava o arquivo de configurações padrão."""
        self.config_data = DEFAULT_CONFIG.copy()
        self.save()
        return self.config_data

    def save(self) -> bool:
        """Salva o estado atual de configurações no disco de forma segura."""
        try:
            temp_path = self.config_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            if os.path.exists(self.config_path):
                os.remove(self.config_path)
            os.rename(temp_path, self.config_path)
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao salvar config.json: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém um valor de configuração pela chave."""
        return self.config_data.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Define um valor de configuração e opcionalmente grava em disco."""
        self.config_data[key] = value
        if auto_save:
            self.save()

    def update_quiz_region(self, x: int, y: int, width: int, height: int) -> None:
        """Atualiza e salva as coordenadas da área do quiz."""
        self.config_data["quiz_region"] = {
            "x": int(x),
            "y": int(y),
            "width": int(width),
            "height": int(height),
            "configured": bool(width > 10 and height > 10)
        }
        self.save()

    def update_next_button(self, x: int, y: int) -> None:
        """Atualiza e salva as coordenadas do botão de avançar."""
        self.config_data["next_button"] = {
            "x": int(x),
            "y": int(y),
            "configured": True
        }
        self.save()
