"""
Módulo de Gerenciamento de Configurações - Mastering Study Quiz
Gerencia a persistência de todas as preferências, flags de automação,
rotação de múltiplas chaves de API e temas em config.json.
"""

import json
import os
from typing import Dict, Any, List

DEFAULT_CONFIG: Dict[str, Any] = {
    # Provedor e Chaves (Suporte a Múltiplas Chaves com Rotação)
    "api_provider": "gemini",
    "api_keys": [],  # Lista de chaves para rotação automática
    "api_key": "",   # Chave principal / ativa
    "active_key_index": 0,
    "model_name": "gemini-2.5-flash",
    "question_mode_hint": "Detecção Automática",
    "language_hint": "Auto-Detectar",
    "enable_computer_vision": True,

    # Regiões e Calibração
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

    # Parâmetros de Automação e Switches Gerais
    "auto_apply": True,           # Clica na resposta automaticamente
    "auto_advance": True,         # Clica em Próximo automaticamente
    "dry_run_mode": False,        # Simulação: analisa e salva no Cérebro sem clicar
    "dark_mode_host": False,      # Injetar CSS escuro se conectado ao host
    "stacked_notifications": True,# Notificações em formato toast
    "show_token_usage": True,     # Exibir uso de tokens no terminal e métricas
    "sound_feedback": True,       # Bip discreto ao concluir resolução
    "compact_mode": False,        # Layout ultra-compacto
    "auto_scroll_logs": True,     # Scroll automático nos logs
    "always_on_top": True,        # Janela sempre no topo (Sidecar Dock)

    # Temporização
    "action_delay": 2.5,
    "transition_delay": 1.5,
    "smooth_mouse": True,

    # Tema Visual Estrito (Apenas 'Light' ou 'Dark')
    "theme_mode": "Light",        # 'Light' (Branco Clean Padrão) ou 'Dark' (Mega Black)
    "glow_effects": True,

    # Motor de Execução
    "execution_engine": "Inteligente (Auto-Híbrido: Visão + Cliques)"
}


class ConfigManager:
    """Gerencia leitura, salvamento e rotação de chaves em config.json."""

    def __init__(self, config_filename: str = "config.json"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(base_dir, config_filename)
        self.config_data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return self._save_defaults()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                merged = DEFAULT_CONFIG.copy()
                for key, val in loaded.items():
                    if isinstance(val, dict) and key in merged and isinstance(merged[key], dict):
                        merged[key].update(val)
                    else:
                        merged[key] = val
                return merged
        except Exception:
            return self._save_defaults()

    def _save_defaults(self) -> Dict[str, Any]:
        self.config_data = DEFAULT_CONFIG.copy()
        self.save()
        return self.config_data

    def save(self) -> bool:
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
        return self.config_data.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        self.config_data[key] = value
        if auto_save:
            self.save()

    def add_api_key(self, key: str) -> None:
        key = key.strip()
        if not key:
            return
        keys = self.config_data.get("api_keys", [])
        if key not in keys:
            keys.append(key)
            self.config_data["api_keys"] = keys
            if not self.config_data.get("api_key"):
                self.config_data["api_key"] = key
            self.save()

    def remove_api_key(self, key: str) -> None:
        keys = self.config_data.get("api_keys", [])
        if key in keys:
            keys.remove(key)
            self.config_data["api_keys"] = keys
            if self.config_data.get("api_key") == key:
                self.config_data["api_key"] = keys[0] if keys else ""
            self.save()

    def get_current_api_key(self) -> str:
        keys = self.config_data.get("api_keys", [])
        if not keys:
            return self.config_data.get("api_key", "").strip()
        idx = self.config_data.get("active_key_index", 0) % len(keys)
        return keys[idx]

    def rotate_api_key(self) -> str:
        keys = self.config_data.get("api_keys", [])
        if len(keys) <= 1:
            return self.get_current_api_key()
        cur_idx = self.config_data.get("active_key_index", 0)
        new_idx = (cur_idx + 1) % len(keys)
        self.config_data["active_key_index"] = new_idx
        self.config_data["api_key"] = keys[new_idx]
        self.save()
        return keys[new_idx]

    def update_quiz_region(self, x: int, y: int, width: int, height: int) -> None:
        self.config_data["quiz_region"] = {
            "x": int(x),
            "y": int(y),
            "width": int(width),
            "height": int(height),
            "configured": bool(width > 10 and height > 10)
        }
        self.save()

    def update_next_button(self, x: int, y: int) -> None:
        self.config_data["next_button"] = {
            "x": int(x),
            "y": int(y),
            "configured": True
        }
        self.save()
