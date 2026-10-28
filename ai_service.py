"""
Módulo de Integração com Serviços de Inteligência Artificial Multimodal (Visão)
Suporta Google Gemini e OpenAI (GPT-4o / GPT-4o-mini) com retorno estrito em JSON estruturado.
"""

import base64
import io
import json
import re
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Dict, Any, Optional
from PIL import Image


@dataclass
class QuizSolution:
    """Estrutura padronizada do resultado da resolução da questão."""
    success: bool
    question: str
    chosen_answer: str
    confidence: float
    target_box_normalized: Dict[str, float]
    raw_response: str
    error_message: Optional[str] = None


SYSTEM_PROMPT = """Você é um especialista em automação e visão computacional para resolução de exames e quizzes de múltipla escolha.
Sua tarefa é analisar a imagem capturada contendo uma questão e suas opções de resposta.

Instruções Estritas:
1. Leia o enunciado e analise cada uma das alternativas visíveis.
2. Determine com máxima precisão a resposta correta da questão.
3. Localize as coordenadas exatas da área clicável da alternativa correta na imagem (o botão de seleção, checkbox ou texto da linha).
4. Retorne OBRIGATORIAMENTE APENAS um objeto JSON válido, sem texto explicativo adicional antes ou depois.

Formato JSON Obrigatório:
{
  "question": "Resumo do enunciado identificado",
  "chosen_answer": "Texto da alternativa correta selecionada",
  "confidence": 0.95,
  "target_box_normalized": {
    "ymin": 0.42,
    "xmin": 0.08,
    "ymax": 0.48,
    "xmax": 0.92
  }
}

Regras das Coordenadas:
- ymin, xmin, ymax, xmax DEVEM ser valores decimais float normalizados entre 0.0 e 1.0 relativos à altura e largura totais da imagem.
- O retângulo deve apontar exatamente para onde o mouse deve clicar para selecionar a opção correta.
"""


class AIService:
    """Serviço unificado para envio de imagem e obtenção da solução via LLMs Multimodais."""

    def __init__(self, provider: str, api_key: str, model_name: str):
        self.provider = provider.lower().strip()
        self.api_key = api_key.strip()
        self.model_name = model_name.strip()

    def update_credentials(self, provider: str, api_key: str, model_name: str) -> None:
        """Atualiza provedor, chave de API e modelo em tempo de execução."""
        self.provider = provider.lower().strip()
        self.api_key = api_key.strip()
        self.model_name = model_name.strip()

    def solve_quiz(self, image: Image.Image) -> QuizSolution:
        """Processa a imagem da questão e retorna a alternativa e coordenadas calculadas."""
        if not self.api_key:
            return QuizSolution(
                success=False,
                question="",
                chosen_answer="",
                confidence=0.0,
                target_box_normalized={"ymin": 0.5, "xmin": 0.5, "ymax": 0.5, "xmax": 0.5},
                raw_response="",
                error_message="Chave de API não informada. Configure a API Key na interface."
            )

        try:
            # Converte a imagem PIL para JPEG em memória
            buffered = io.BytesIO()
            # Converte RGBA para RGB se necessário para salvar como JPEG
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            image.save(buffered, format="JPEG", quality=90)
            img_bytes = buffered.getvalue()
            b64_image = base64.b64encode(img_bytes).decode("utf-8")

            if self.provider == "gemini":
                raw_text = self._call_gemini_api(b64_image)
            elif self.provider == "openai":
                raw_text = self._call_openai_api(b64_image)
            else:
                return QuizSolution(
                    success=False,
                    question="",
                    chosen_answer="",
                    confidence=0.0,
                    target_box_normalized={},
                    raw_response="",
                    error_message=f"Provedor desconhecido: '{self.provider}'"
                )

            return self._parse_json_response(raw_text)

        except Exception as ex:
            return QuizSolution(
                success=False,
                question="",
                chosen_answer="",
                confidence=0.0,
                target_box_normalized={},
                raw_response="",
                error_message=f"Erro na requisição à IA: {str(ex)}"
            )

    def _call_gemini_api(self, b64_image: str) -> str:
        """Envia requisição direta para a Google Gemini REST API v1beta."""
        model = self.model_name if self.model_name else "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": b64_image
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

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if not candidates:
                    raise ValueError("Nenhum candidato de resposta retornado pelo Gemini.")
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise ValueError("Resposta vazia retornada pelo Gemini.")
                return parts[0].get("text", "")
        except urllib.error.HTTPError as http_err:
            error_body = http_err.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {http_err.code} Gemini: {error_body}")

    def _call_openai_api(self, b64_image: str) -> str:
        """Envia requisição direta para a OpenAI Chat Completions API."""
        model = self.model_name if self.model_name else "gpt-4o-mini"
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
                                "url": f"data:image/jpeg;base64,{b64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                choices = res_data.get("choices", [])
                if not choices:
                    raise ValueError("Nenhuma escolha retornada pela OpenAI.")
                return choices[0].get("message", {}).get("content", "")
        except urllib.error.HTTPError as http_err:
            error_body = http_err.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {http_err.code} OpenAI: {error_body}")

    def _parse_json_response(self, text: str) -> QuizSolution:
        """Extrai e valida o JSON retornado pela IA, lidando com markdown e formatações."""
        clean_text = text.strip()
        # Remove blocos markdown caso existam
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        # Busca bloco JSON com regex se ainda houver resíduo
        match = re.search(r"\{[\s\S]*\}", clean_text)
        if match:
            clean_text = match.group(0)

        data = json.loads(clean_text)

        question = str(data.get("question", "Questão identificada"))
        chosen_answer = str(data.get("chosen_answer", "Alternativa selecionada"))
        confidence = float(data.get("confidence", 1.0))
        box = data.get("target_box_normalized", {})

        # Validação e saneamento dos limites das coordenadas normalizadas
        ymin = max(0.0, min(1.0, float(box.get("ymin", 0.5))))
        xmin = max(0.0, min(1.0, float(box.get("xmin", 0.1))))
        ymax = max(0.0, min(1.0, float(box.get("ymax", 0.55))))
        xmax = max(0.0, min(1.0, float(box.get("xmax", 0.9))))

        if ymax <= ymin:
            ymax = min(1.0, ymin + 0.05)
        if xmax <= xmin:
            xmax = min(1.0, xmin + 0.1)

        sanitized_box = {
            "ymin": ymin,
            "xmin": xmin,
            "ymax": ymax,
            "xmax": xmax
        }

        return QuizSolution(
            success=True,
            question=question,
            chosen_answer=chosen_answer,
            confidence=confidence,
            target_box_normalized=sanitized_box,
            raw_response=text,
            error_message=None
        )
