"""
Módulo de Visão Computacional e Inteligência Artificial Multimodal - Mastering Study Quiz
Analisa a imagem capturada e retorna JSON com resposta, coordenadas e classificação de elementos visuais.
"""

import io
import json
import re
import base64
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Dict, Any, Optional
from PIL import Image


@dataclass
class VisionAnalysisResult:
    """Resultado estruturado retornado pela IA Multimodal."""
    success: bool
    pergunta_extraida: str
    alternativa_correta: str
    confianca: float
    coordenadas_resposta: Dict[str, float]  # {"x_norm": float, "y_norm": float}
    possui_elemento_visual: bool
    categoria_imagem: str                   # "Gráfico", "Tabela", "Diagrama", "Fórmula", "Mapa", "Texto Puro"
    contexto_imagem: str                    # Explicação didática da figura
    bounding_box_elemento: Dict[str, float] # {"ymin": float, "xmin": float, "ymax": float, "xmax": float}
    raw_response: str
    error_message: Optional[str] = None


SYSTEM_PROMPT = """Você é um especialista em Visão Computacional, Exames Online e Automação Educacional.
Sua tarefa é analisar minuciosamente o print da tela contendo uma questão de quiz ou prova.

Você deve responder OBRIGATORIAMENTE APENAS com um objeto JSON estrito com os seguintes campos:
{
  "pergunta_extraida": "Texto completo ou resumido do enunciado da questão",
  "alternativa_correta": "Texto e letra da alternativa correta",
  "confianca": 0.98,
  "coordenadas_resposta": {
    "x_norm": 0.52,
    "y_norm": 0.45
  },
  "possui_elemento_visual": true,
  "categoria_imagem": "Gráfico",
  "contexto_imagem": "Gráfico cartesiano mostrando crescimento exponencial de bactérias ao longo do tempo.",
  "bounding_box_elemento": {
    "ymin": 0.12,
    "xmin": 0.05,
    "ymax": 0.48,
    "xmax": 0.95
  }
}

REGRAS ESTRITAS:
1. "coordenadas_resposta": Ponto exato normalizado (0.0 a 1.0) onde o mouse deve clicar (centro do botão de rádio, checkbox ou linha da opção correta).
2. "possui_elemento_visual": Defina como true se houver qualquer figura, gráfico, tabela, charge, fórmula complexa ou diagrama no enunciado. Defina como false se for apenas texto puro.
3. "categoria_imagem": Classifique com um destes rótulos: "Gráfico", "Tabela", "Diagrama", "Fórmula", "Mapa", "Charge", "Outros", ou "Texto Puro".
4. "contexto_imagem": Explicação concisa e clara do que a imagem/gráfico mostra para servir de resumo de estudo no Cérebro.
5. "bounding_box_elemento": Se houver figura/gráfico, forneça a caixa delimitadora normalizada (ymin, xmin, ymax, xmax entre 0.0 e 1.0) para que o programa possa recortar exatamente o elemento visual. Se não houver, envie valores vazios ou 0.
6. Não adicione nenhum texto, introdução ou bloco markdown fora do objeto JSON.
"""


class AIVisionService:
    """Gerencia a comunicação com provedores de IA Multimodal (Gemini e OpenAI)."""

    def __init__(self, provider: str = "gemini", api_key: str = "", model_name: str = "gemini-2.5-flash"):
        self.provider = provider.lower().strip()
        self.api_key = api_key.strip()
        self.model_name = model_name.strip()

    def update_credentials(self, provider: str, api_key: str, model_name: str) -> None:
        self.provider = provider.lower().strip()
        self.api_key = api_key.strip()
        self.model_name = model_name.strip()

    def analyze_quiz_image(self, image: Image.Image) -> VisionAnalysisResult:
        """Processa a captura de tela e retorna a resposta e os recortes detectados."""
        if not self.api_key:
            return VisionAnalysisResult(
                success=False,
                pergunta_extraida="",
                alternativa_correta="",
                confianca=0.0,
                coordenadas_resposta={"x_norm": 0.5, "y_norm": 0.5},
                possui_elemento_visual=False,
                categoria_imagem="Texto Puro",
                contexto_imagem="",
                bounding_box_elemento={},
                raw_response="",
                error_message="Chave de API não informada. Insira sua chave nas Configurações."
            )

        try:
            buffered = io.BytesIO()
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            image.save(buffered, format="JPEG", quality=90)
            b64_img = base64.b64encode(buffered.getvalue()).decode("utf-8")

            if self.provider == "gemini":
                raw_text = self._call_gemini(b64_img)
            elif self.provider == "openai":
                raw_text = self._call_openai(b64_img)
            else:
                raise ValueError(f"Provedor não suportado: {self.provider}")

            return self._parse_json(raw_text)

        except Exception as e:
            return VisionAnalysisResult(
                success=False,
                pergunta_extraida="",
                alternativa_correta="",
                confianca=0.0,
                coordenadas_resposta={"x_norm": 0.5, "y_norm": 0.5},
                possui_elemento_visual=False,
                categoria_imagem="Texto Puro",
                contexto_imagem="",
                bounding_box_elemento={},
                raw_response="",
                error_message=f"Erro na IA ({self.provider}): {str(e)}"
            )

    def _call_gemini(self, b64_img: str) -> str:
        model = self.model_name or "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": b64_img
                            }
                        }
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
                raise ValueError("Nenhum candidato retornado pelo Gemini.")
            return candidates[0]["content"]["parts"][0]["text"]

    def _call_openai(self, b64_img: str) -> str:
        model = self.model_name or "gpt-4o-mini"
        url = "https://api.openai.com/v1/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": SYSTEM_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_img}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]

    def _parse_json(self, raw_text: str) -> VisionAnalysisResult:
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

        pergunta = str(data.get("pergunta_extraida", "Pergunta identificada"))
        resposta = str(data.get("alternativa_correta", "Alternativa selecionada"))
        confianca = float(data.get("confianca", 1.0))

        # Coordenadas do clique na resposta
        coords_raw = data.get("coordenadas_resposta", {})
        x_norm = max(0.0, min(1.0, float(coords_raw.get("x_norm", coords_raw.get("x", 0.5)))))
        y_norm = max(0.0, min(1.0, float(coords_raw.get("y_norm", coords_raw.get("y", 0.5)))))

        possui_elemento = bool(data.get("possui_elemento_visual", False))
        categoria = str(data.get("categoria_imagem", "Texto Puro")).strip() or "Texto Puro"
        contexto = str(data.get("contexto_imagem", "")).strip()

        # Bounding box da figura/gráfico para recorte
        bb_raw = data.get("bounding_box_elemento", {})
        ymin = max(0.0, min(1.0, float(bb_raw.get("ymin", 0.0))))
        xmin = max(0.0, min(1.0, float(bb_raw.get("xmin", 0.0))))
        ymax = max(0.0, min(1.0, float(bb_raw.get("ymax", 0.0))))
        xmax = max(0.0, min(1.0, float(bb_raw.get("xmax", 0.0))))

        bbox = {"ymin": ymin, "xmin": xmin, "ymax": ymax, "xmax": xmax}

        return VisionAnalysisResult(
            success=True,
            pergunta_extraida=pergunta,
            alternativa_correta=resposta,
            confianca=confianca,
            coordenadas_resposta={"x_norm": x_norm, "y_norm": y_norm},
            possui_elemento_visual=possui_elemento,
            categoria_imagem=categoria,
            contexto_imagem=contexto,
            bounding_box_elemento=bbox,
            raw_response=raw_text,
            error_message=None
        )
