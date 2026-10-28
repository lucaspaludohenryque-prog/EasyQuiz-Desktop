"""
Módulo de Visão Computacional e Inteligência Artificial Multimodal - Mastering Study Quiz
Analisa a imagem capturada, injeta contexto RAG, suporta rotação de múltiplas chaves
e retorna respostas estruturadas com rationale explicativo e bounding boxes.
"""

import io
import time
import json
import re
import base64
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from PIL import Image

from config_manager import ConfigManager


@dataclass
class VisionAnalysisResult:
    success: bool
    pergunta_extraida: str
    alternativa_correta: str
    rationale: str
    confianca: float
    coordenadas_resposta: Dict[str, float]
    possui_elemento_visual: bool
    categoria_imagem: str
    contexto_imagem: str
    bounding_box_elemento: Dict[str, float]
    prompt_enviado: str
    tokens_usados: int
    latencia_ms: int
    raw_response: str
    error_message: Optional[str] = None


SYSTEM_PROMPT_TEMPLATE = """Você é o motor de IA do Mastering Study Quiz, especialista em exames, provas e visão computacional.
Analise detalhadamente o print da questão do quiz exibida na tela.

{rag_section}

{mode_hint_section}
{lang_hint_section}

Retorne OBRIGATORIAMENTE APENAS um objeto JSON estrito com os campos:
{{
  "pergunta_extraida": "Enunciado completo ou resumido da questão",
  "alternativa_correta": "Texto e letra da alternativa correta",
  "rationale": "Explicação passo a passo demonstrando por que esta alternativa está correta e por que as outras estão incorretas.",
  "confianca": 0.98,
  "coordenadas_resposta": {{
    "x_norm": 0.52,
    "y_norm": 0.45
  }},
  "possui_elemento_visual": true,
  "categoria_imagem": "Grafico",
  "contexto_imagem": "Gráfico cartesiano mostrando crescimento exponencial...",
  "bounding_box_elemento": {{
    "ymin": 0.10,
    "xmin": 0.05,
    "ymax": 0.45,
    "xmax": 0.95
  }}
}}

REGRAS:
1. "coordenadas_resposta": Coordenadas normalizadas (0.0 a 1.0) do centro da opção/botão clicável para a resposta correta.
2. "possui_elemento_visual": true se houver figura, gráfico, tabela, diagrama, charge ou fórmula complexa.
3. "categoria_imagem": Escolha exatamente uma destas tags: "Grafico", "Tabela", "Diagrama", "Formula", "Mapa", "Outros", ou "Texto Puro".
4. "contexto_imagem": Explicação didática do que o gráfico/figura representa para compor o Cérebro de estudos.
5. "bounding_box_elemento": Coordenadas (ymin, xmin, ymax, xmax entre 0.0 e 1.0) para recorte exclusivo do gráfico/figura.
6. Apenas o JSON válido, sem texto adicional.
"""


class AIVisionService:
    """Serviço de IA com suporte a rotação de tokens, RAG e medição de latência."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def analyze_quiz_image(self, image: Image.Image, rag_context: str = "") -> VisionAnalysisResult:
        api_key = self.config_manager.get_current_api_key()
        if not api_key:
            return VisionAnalysisResult(
                success=False,
                pergunta_extraida="",
                alternativa_correta="",
                rationale="",
                confianca=0.0,
                coordenadas_resposta={"x_norm": 0.5, "y_norm": 0.5},
                possui_elemento_visual=False,
                categoria_imagem="Texto Puro",
                contexto_imagem="",
                bounding_box_elemento={},
                prompt_enviado="",
                tokens_usados=0,
                latencia_ms=0,
                raw_response="",
                error_message="Nenhuma chave de API configurada. Adicione uma chave em Configurações > Tokens."
            )

        start_time = time.time()

        # Montagem do prompt com RAG e Dicas de Modo
        mode_hint = self.config_manager.get("question_mode_hint", "Detecção Automática")
        lang_hint = self.config_manager.get("language_hint", "Auto-Detectar")

        rag_sec = f"Contexto RAG do Cérebro:\n{rag_context}" if rag_context else ""
        mode_sec = f"Dica de Formato: {mode_hint}" if mode_hint != "Detecção Automática" else ""
        lang_sec = f"Idioma Preferencial de Resposta: {lang_hint}" if lang_hint != "Auto-Detectar" else ""

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            rag_section=rag_sec,
            mode_hint_section=mode_sec,
            lang_hint_section=lang_sec
        )

        try:
            buffered = io.BytesIO()
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            image.save(buffered, format="JPEG", quality=90)
            b64_img = base64.b64encode(buffered.getvalue()).decode("utf-8")

            provider = self.config_manager.get("api_provider", "gemini")
            raw_text, tokens_est = self._execute_request_with_rotation(provider, system_prompt, b64_img)

            latency_ms = int((time.time() - start_time) * 1000)
            parsed = self._parse_json(raw_text, system_prompt, tokens_est, latency_ms)
            return parsed

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return VisionAnalysisResult(
                success=False,
                pergunta_extraida="",
                alternativa_correta="",
                rationale="",
                confianca=0.0,
                coordenadas_resposta={"x_norm": 0.5, "y_norm": 0.5},
                possui_elemento_visual=False,
                categoria_imagem="Texto Puro",
                contexto_imagem="",
                bounding_box_elemento={},
                prompt_enviado=system_prompt,
                tokens_usados=0,
                latencia_ms=latency_ms,
                raw_response="",
                error_message=f"Falha na consulta à IA: {str(e)}"
            )

    def _execute_request_with_rotation(self, provider: str, prompt: str, b64_img: str) -> Tuple[str, int]:
        """Tenta a requisição e, em caso de erro 429 (quota), rotaciona automaticamente a chave."""
        keys = self.config_manager.get("api_keys", [])
        attempts = max(1, len(keys))

        last_error = None
        for _ in range(attempts):
            api_key = self.config_manager.get_current_api_key()
            try:
                if provider == "gemini":
                    return self._call_gemini(api_key, prompt, b64_img)
                else:
                    return self._call_openai(api_key, prompt, b64_img)
            except urllib.error.HTTPError as http_err:
                last_error = http_err
                if http_err.code in (429, 403) and len(keys) > 1:
                    # Rotaciona para a próxima chave
                    self.config_manager.rotate_api_key()
                    continue
                else:
                    raise http_err

        if last_error:
            raise last_error
        raise RuntimeError("Nenhuma chave válida para requisição.")

    def _call_gemini(self, api_key: str, prompt: str, b64_img: str) -> Tuple[str, int]:
        model = self.config_manager.get("model_name", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("Nenhuma resposta retornada pelo Gemini.")

            # Extração de tokens usados
            usage = data.get("usageMetadata", {})
            tokens_total = usage.get("totalTokenCount", 450)

            return candidates[0]["content"]["parts"][0]["text"], tokens_total

    def _call_openai(self, api_key: str, prompt: str, b64_img: str) -> Tuple[str, int]:
        model = self.config_manager.get("model_name", "gpt-4o-mini")
        url = "https://api.openai.com/v1/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}", "detail": "high"}}
                    ]
                }
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            usage = data.get("usage", {})
            tokens_total = usage.get("total_tokens", 400)
            return data["choices"][0]["message"]["content"], tokens_total

    def _parse_json(self, raw_text: str, prompt_enviado: str, tokens: int, latencia_ms: int) -> VisionAnalysisResult:
        clean = raw_text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        match = re.search(r"\{[\s\S]*\}", clean)
        if match:
            clean = match.group(0)

        data = json.loads(clean)

        pergunta = str(data.get("pergunta_extraida", "Questão identificada"))
        resposta = str(data.get("alternativa_correta", "Alternativa selecionada"))
        rationale = str(data.get("rationale", "Justificativa não informada pela IA."))
        confianca = float(data.get("confianca", 1.0))

        coords_raw = data.get("coordenadas_resposta", {})
        x_norm = max(0.0, min(1.0, float(coords_raw.get("x_norm", coords_raw.get("x", 0.5)))))
        y_norm = max(0.0, min(1.0, float(coords_raw.get("y_norm", coords_raw.get("y", 0.5)))))

        possui_elemento = bool(data.get("possui_elemento_visual", False))
        categoria = str(data.get("categoria_imagem", "Texto Puro")).strip() or "Texto Puro"
        contexto = str(data.get("contexto_imagem", "")).strip()

        bb_raw = data.get("bounding_box_elemento", {})
        bbox = {
            "ymin": max(0.0, min(1.0, float(bb_raw.get("ymin", 0.0)))),
            "xmin": max(0.0, min(1.0, float(bb_raw.get("xmin", 0.0)))),
            "ymax": max(0.0, min(1.0, float(bb_raw.get("ymax", 0.0)))),
            "xmax": max(0.0, min(1.0, float(bb_raw.get("xmax", 0.0))))
        }

        return VisionAnalysisResult(
            success=True,
            pergunta_extraida=pergunta,
            alternativa_correta=resposta,
            rationale=rationale,
            confianca=confianca,
            coordenadas_resposta={"x_norm": x_norm, "y_norm": y_norm},
            possui_elemento_visual=possui_elemento,
            categoria_imagem=categoria,
            contexto_imagem=contexto,
            bounding_box_elemento=bbox,
            prompt_enviado=prompt_enviado,
            tokens_usados=tokens,
            latencia_ms=latencia_ms,
            raw_response=raw_text,
            error_message=None
        )
