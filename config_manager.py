"""
Módulo de Gerenciamento de Configurações - Mastering Study Quiz
Gerencia a persistência em config.json com suporte a Pool de Chaves de API
(Rotação Automática Anti-Rate Limit), Motor Híbrido, Janela Inteligente e Temas.
"""

import json
import os
import shutil
from typing import Dict, Any, List, Optional, Tuple

DEFAULT_CONFIG: Dict[str, Any] = {
    # 1. Provedor e Pool de Chaves com Rotação Automática (Anti-Rate Limit 429)
    "api_provider": "gemini",
    "api_keys": [],
    "api_key": "",
    "active_key_index": 0,
    "model_name": "gemini-2.5-flash",
    "question_mode_hint": "Detecção Automática",
    "language_hint": "Auto-Detectar",
    "enable_computer_vision": True,

    # 2. Motor Híbrido Real (Visão Pura + Ponte DOM)
    "execution_engine": "Inteligente (Auto-Híbrido)",
    "dark_mode_host": False,
    "cdp_url": "http://localhost:9222",

    # 3. Memória RAG Local (Zero Tokens)
    "enable_rag_memory": True,
    "rag_similarity_threshold": 0.95,

    # 4. Auto-Digitação Humanizada (Questões Discursivas)
    "human_typing_speed": True,
    "typing_min_delay_ms": 30,
    "typing_max_delay_ms": 85,

    # 5. Simulador de Testes Integrado e Modo Dry-Run (Mira na Tela)
    "dry_run_mode": False,
    "test_sandbox_url": "quiz_test_sandbox.html",

    # 6. Parâmetros de Automação & Switches Gerais
    "auto_apply": True,
    "auto_advance": True,
    "stacked_notifications": True,
    "show_token_usage": True,
    "sound_feedback": True,
    "compact_mode": False,
    "auto_scroll_logs": True,

    # 7. Janela Inteligente (Sidecar Dock & Hotkeys)
    "always_on_top": True,
    "stealth_hotkey": "alt+q",
    "autopilot_hotkey": "f8",
    "emergency_stop_hotkey": "esc",

    # 8. Calibração de Regiões de Tela
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

    # 9. Temporização e Movimento Suave do Cursor
    "action_delay": 2.0,
    "transition_delay": 1.2,
    "smooth_mouse": True,

    # 10. Temas Visuais Estritos (Apenas 'Light' e 'Dark')
    "theme_mode": "Light",
    "glow_effects": True
}


class ConfigManager:
    """Gerenciador unificado de configurações do Mastering Study Quiz."""

    def __init__(self, config_filename: str = "config.json"):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, config_filename)
        self.config_data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """Carrega as configurações com fallback seguro para os padrões."""
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
        except Exception as e:
            print(f"[CONFIG] Aviso: Falha ao ler {self.config_path} ({e}). Recriando padrões.")
            return self._save_defaults()

    def _save_defaults(self) -> Dict[str, Any]:
        self.config_data = DEFAULT_CONFIG.copy()
        self.save()
        return self.config_data

    def save(self) -> bool:
        """Salva atomicamente em disco usando arquivo temporário para evitar corrupção."""
        try:
            temp_path = self.config_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            if os.path.exists(self.config_path):
                os.remove(self.config_path)
            os.rename(temp_path, self.config_path)
            return True
        except Exception as e:
            print(f"[CONFIG] ERRO: Falha ao salvar configurações: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.config_data.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        self.config_data[key] = value
        if auto_save:
            self.save()

    # =========================================================================
    # Pool de Chaves com Rotação Automática (Anti-Rate Limit)
    # =========================================================================
    def add_api_key(self, key: str) -> bool:
        """Adiciona uma chave ao pool se ainda não existir."""
        clean_key = key.strip()
        if not clean_key:
            return False

        keys: List[str] = list(self.config_data.get("api_keys", []))
        if clean_key not in keys:
            keys.append(clean_key)
            self.config_data["api_keys"] = keys
            if not self.config_data.get("api_key"):
                self.config_data["api_key"] = clean_key
                self.config_data["active_key_index"] = 0
            self.save()
            return True
        return False

    def remove_api_key(self, key: str) -> bool:
        """Remove uma chave do pool."""
        clean_key = key.strip()
        keys: List[str] = list(self.config_data.get("api_keys", []))
        if clean_key in keys:
            keys.remove(clean_key)
            self.config_data["api_keys"] = keys
            if self.config_data.get("api_key") == clean_key:
                new_key = keys[0] if keys else ""
                self.config_data["api_key"] = new_key
                self.config_data["active_key_index"] = 0
            self.save()
            return True
        return False

    def get_all_api_keys(self) -> List[str]:
        return list(self.config_data.get("api_keys", []))

    def get_active_api_key(self) -> str:
        """Retorna a chave atualmente ativa no pool."""
        keys = self.config_data.get("api_keys", [])
        if not keys:
            return str(self.config_data.get("api_key", "")).strip()
        idx = int(self.config_data.get("active_key_index", 0)) % len(keys)
        return keys[idx]

    def rotate_api_key(self, reason: str = "429 Rate Limit") -> Tuple[str, int]:
        """
        Rotaciona instantaneamente para a próxima chave da lista.
        Retorna uma tupla (nova_chave, novo_indice).
        """
        keys = self.config_data.get("api_keys", [])
        if not keys:
            active = self.get_active_api_key()
            return active, 0

        cur_idx = int(self.config_data.get("active_key_index", 0))
        new_idx = (cur_idx + 1) % len(keys)
        new_key = keys[new_idx]

        self.config_data["active_key_index"] = new_idx
        self.config_data["api_key"] = new_key
        self.save()

        masked_key = f"{new_key[:6]}...{new_key[-4:]}" if len(new_key) > 10 else "***"
        print(f"[POOL] Rotação de Chave acionada ({reason}). Nova chave ativa: índice {new_idx} ({masked_key})")
        return new_key, new_idx

    # =========================================================================
    # Calibração e Regiões
    # =========================================================================
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

    # =========================================================================
    # Backup, Exportação e Reset
    # =========================================================================
    def export_config(self, dest_path: str) -> bool:
        """Exporta o arquivo de configurações para backup."""
        try:
            with open(dest_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[CONFIG] Erro ao exportar: {e}")
            return False

    def import_config(self, source_path: str) -> bool:
        """Importa configurações de um arquivo JSON externo."""
        if not os.path.exists(source_path):
            return False
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                merged = DEFAULT_CONFIG.copy()
                for key, val in loaded.items():
                    if isinstance(val, dict) and key in merged and isinstance(merged[key], dict):
                        merged[key].update(val)
                    else:
                        merged[key] = val
                self.config_data = merged
                self.save()
                return True
        except Exception as e:
            print(f"[CONFIG] Erro ao importar: {e}")
            return False

    def reset_to_defaults(self) -> None:
        """Restaura os valores padrão de fábrica."""
        self.config_data = DEFAULT_CONFIG.copy()
        self.save()
