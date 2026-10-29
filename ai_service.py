"""
Módulo de Inteligência Artificial e Visão Computacional - Mastering Study Quiz
Integração com Google Gemini (gemini-2.5-flash) com suporte a:
1. Envio da imagem recortada com prompt de sistema estrito.
2. Extração e validação do JSON com 'resposta', 'x_percent' e 'y_percent'.
3. Pool de Chaves com rotação automática em caso de Rate Limit (Erro 429).
4. Consulta à Memória RAG Local (Zero Tokens) antes da chamada de API.
"""

import io
import time
import json
import re
import base64
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Tuple
from PIL import Image

from config_manager import ConfigManager
from brain_storage import BrainStorage


@dataclass
class QuizSolutionResult:
    """Estrutura validada da resposta da IA para a resolução da questão."""
    success: bool
    resposta: str
    x_percent: float
    y_percent: float
    rationale: str
    confianca: float
    categoria: str
    contexto_imagem: str
    tokens_usados: int
    latencia_ms: int
    is_rag_cache: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


SYSTEM_PROMPT = """Você é um assistente de provas. Leia a imagem que contém uma questão e suas alternativas. Retorne estritamente um JSON com a chave 'resposta' contendo o texto da alternativa correta, e as chaves 'x_percent' e 'y_percent' indicando a posição relativa (de 0.0 a 1.0) de onde fica a bolinha/caixa de seleção da resposta correta na imagem, para que um robô possa clicar.

Retorne OBRIGATORIAMENTE APENAS o JSON válido no seguinte formato:
{
  "resposta": "Texto da alternativa correta",
  "x_percent": 0.08,
  "y_percent": 0.45,
  "rationale": "Explicação resumida do porquê esta é a alternativa correta",
  "confianca": 0.95,
  "categoria": "Texto",
  "contexto_visual": "Descrição do que a imagem contém se houver gráfico ou tabela"
}
"""


class AIService:
    """Serviço de IA Multimodal para resolução de quizzes com Google Gemini."""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        brain_storage: Optional[BrainStorage] = None
    ):
        self.config_manager = config_manager or ConfigManager()
        self.brain_storage = brain_storage or BrainStorage()

    def resolve_question_image(
        self,
        image: Image.Image,
        max_retries_keys: int = 3
    ) -> QuizSolutionResult:
        """
        Envia a imagem recortada para a IA e retorna a solução estruturada com coordenadas.
        Consulta primeiro a memória RAG local (Zero Tokens).
        Executa rotação automática de chave em caso de Rate Limit (Erro 429).
        """
        start_time = time.time()

        # 1. Consulta à Memória RAG Local (Zero Tokens)
        if self.config_manager.get("enable_rag_memory", True) and self.brain_storage:
            try:
                cached = self.brain_storage.lookup_rag("", question_image=image)
                if cached:
                    lat_ms = int((time.time() - start_time) * 1000)
                    coords = cached.get("coordenadas", {})
                    return QuizSolutionResult(
                        success=True,
                        resposta=cached.get("resposta", ""),
                        x_percent=float(coords.get("x_percent", 0.08)),
                        y_percent=float(coords.get("y_percent", 0.45)),
                        rationale=cached.get("rationale", "Resposta recuperada da Memória RAG Local."),
                        confianca=1.0,
                        categoria=cached.get("categoria", "Texto"),
                        contexto_imagem=cached.get("contexto_imagem", ""),
                        tokens_usados=0,
                        latencia_ms=lat_ms,
                        is_rag_cache=True
                    )
            except Exception as e:
                print(f"[IA] Aviso na consulta RAG local: {e}")

        # 2. Resolução Online via API Gemini com Pool de Chaves
        keys = self.config_manager.get_all_api_keys()
        attempts = 0
        total_attempts = max(1, len(keys)) if keys else 1

        last_error = ""

        while attempts < total_attempts:
            current_key = self.config_manager.get_active_api_key()
            if not current_key:
                return QuizSolutionResult(
                    success=False,
                    resposta="",
                    x_percent=0.0,
                    y_percent=0.0,
                    rationale="",
                    confianca=0.0,
                    categoria="Texto",
                    contexto_imagem="",
                    tokens_usados=0,
                    latencia_ms=0,
                    error_message="Nenhuma chave de API configurada no aplicativo. Insira uma chave Gemini nas Configurações."
                )

            model_name = self.config_manager.get("model_name", "gemini-2.5-flash")

            try:
                raw_text, tokens = self._call_gemini_api(
                    api_key=current_key,
                    model_name=model_name,
                    image=image
                )

                parsed_json = self._parse_json_response(raw_text)
                if not parsed_json:
                    raise ValueError(f"A IA não retornou um JSON válido: {raw_text[:120]}")

                lat_ms = int((time.time() - start_time) * 1000)

                resp_str = str(parsed_json.get("resposta", "")).strip()
                x_pct = float(parsed_json.get("x_percent", 0.08))
                y_pct = float(parsed_json.get("y_percent", 0.45))
                # Limita coordenadas percentuais entre 0.0 e 1.0
                x_pct = max(0.0, min(1.0, x_pct))
                y_pct = max(0.0, min(1.0, y_pct))

                rationale = str(parsed_json.get("rationale", "Alternativa selecionada por raciocínio lógico da IA."))
                conf = float(parsed_json.get("confianca", 0.95))
                categoria = str(parsed_json.get("categoria", "Texto"))
                contexto_vis = str(parsed_json.get("contexto_visual", ""))

                result = QuizSolutionResult(
                    success=True,
                    resposta=resp_str,
                    x_percent=x_pct,
                    y_percent=y_pct,
                    rationale=rationale,
                    confianca=conf,
                    categoria=categoria,
                    contexto_imagem=contexto_vis,
                    tokens_usados=tokens,
                    latencia_ms=lat_ms,
                    is_rag_cache=False
                )

                # Salva a sessão no Cérebro para aprendizado RAG futuro
                if self.brain_storage:
                    try:
                        self.brain_storage.save_session(
                            pergunta=resp_str,
                            resposta=resp_str,
                            rationale=rationale,
                            confianca=conf,
                            categoria=categoria,
                            contexto_imagem=contexto_vis,
                            imagem_recorte=image,
                            coordenadas_clique={"x_percent": x_pct, "y_percent": y_pct},
                            prompt_enviado=SYSTEM_PROMPT,
                            modelo=model_name,
                            latencia_ms=lat_ms,
                            tokens_usados=tokens
                        )
                    except Exception as e:
                        print(f"[IA] Aviso ao persistir sessão no Cérebro: {e}")

                return result

            except urllib.error.HTTPError as http_err:
                last_error = f"HTTP {http_err.code}: {http_err.reason}"
                if http_err.code in (429, 403) and len(keys) > 1:
                    print(f"[IA] Limite atingido na chave atual (HTTP {http_err.code}). Acionando rotação automática...")
                    self.config_manager.rotate_api_key(reason=f"HTTP {http_err.code}")
                    attempts += 1
                    time.sleep(0.3)
                    continue
                else:
                    break
            except Exception as e:
                last_error = str(e)
                if "429" in last_error and len(keys) > 1:
                    self.config_manager.rotate_api_key(reason="Quota / 429")
                    attempts += 1
                    time.sleep(0.3)
                    continue
                break

        return QuizSolutionResult(
            success=False,
            resposta="",
            x_percent=0.0,
            y_percent=0.0,
            rationale="",
            confianca=0.0,
            categoria="Texto",
            contexto_imagem="",
            tokens_usados=0,
            latencia_ms=int((time.time() - start_time) * 1000),
            error_message=f"Falha na análise da IA: {last_error}"
        )

    def _call_gemini_api(self, api_key: str, model_name: str, image: Image.Image) -> Tuple[str, int]:
        """
        Envia a imagem e o prompt para a API do Google Gemini via endpoint REST universal.
        Não depende de versão específica de SDK no cliente, garantindo 100% de estabilidade.
        """
        # Converte a imagem em JPEG base64 em memória
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=88)
        img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        clean_model = model_name if model_name.startswith("gemini") else "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": img_b64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        json_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=json_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=18) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Nenhuma resposta gerada pela API do Gemini.")

        parts = candidates[0].get("content", {}).get("parts", [])
        text_response = parts[0].get("text", "") if parts else ""

        usage = data.get("usageMetadata", {})
        tokens = usage.get("totalTokenCount", 180)

        return text_response, tokens

    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Limpa tags markdown e decodifica o JSON retornado."""
        if not text:
            return None

        clean = text.strip()
        # Remove blocos markdown `json ... `
        if "`" in clean:
            match = re.search(r"`(?:json)?\s*([\s\S]*?)\s*`", clean)
            if match:
                clean = match.group(1).strip()

        try:
            return json.loads(clean)
        except Exception:
            # Tenta encontrar o primeiro bloco delimitado por chaves { ... }
            match = re.search(r"(\{[\s\S]*\})", clean)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return None


# Alias de compatibilidade
AIVisionService = AIService
