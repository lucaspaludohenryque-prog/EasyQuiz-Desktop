"""
Módulo de Métricas e Cronômetro - Mastering Study Quiz
Gerencia temporização precisa, contadores de tokens, médias por questão e histórico de sessão.
"""

import time
from typing import List, Dict, Any, Optional


class MetricsTracker:
    """Rastreia métricas em tempo real para a Tela de Métricas e relatórios."""

    def __init__(self):
        self.session_start_time: Optional[float] = None
        self.current_question_start_time: Optional[float] = None
        self.is_question_active: bool = False

        self.total_tokens_consumed: int = 0
        self.current_question_tokens: int = 0
        self.questions_history: List[Dict[str, Any]] = []

    def start_session(self) -> None:
        if self.session_start_time is None:
            self.session_start_time = time.time()

    def start_question(self) -> None:
        self.start_session()
        self.current_question_start_time = time.time()
        self.is_question_active = True
        self.current_question_tokens = 0

    def finish_question(
        self,
        question_idx: int,
        answer: str,
        has_visual: bool,
        category: str,
        tokens: int,
        latency_ms: int
    ) -> Dict[str, Any]:
        elapsed = 0.0
        if self.current_question_start_time:
            elapsed = time.time() - self.current_question_start_time

        self.total_tokens_consumed += tokens
        self.current_question_tokens = tokens
        self.is_question_active = False

        item = {
            "numero": question_idx,
            "tempo_s": round(elapsed, 2),
            "tempo_formatado": f"{elapsed:.2f}s",
            "resposta": answer,
            "possui_visual": has_visual,
            "categoria": category,
            "tokens": tokens,
            "latencia_ms": latency_ms,
            "timestamp": time.strftime("%H:%M:%S")
        }
        self.questions_history.append(item)
        return item

    def get_current_question_elapsed(self) -> float:
        if self.is_question_active and self.current_question_start_time:
            return time.time() - self.current_question_start_time
        return 0.0

    def get_total_session_elapsed(self) -> float:
        if self.session_start_time:
            return time.time() - self.session_start_time
        return 0.0

    def get_average_time(self) -> float:
        if not self.questions_history:
            return 0.0
        total = sum(q["tempo_s"] for q in self.questions_history)
        return round(total / len(self.questions_history), 2)

    def format_stopwatch(self, seconds: float) -> str:
        """Formata segundos em 'MM:SS.ms' (ex: 01:23.45)."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 100)
        return f"{mins:02d}:{secs:02d}.{ms:02d}"

    def format_minutes_seconds(self, seconds: float) -> str:
        """Formata segundos em 'MM:SS'."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def generate_report_markdown(self) -> str:
        """Gera um relatório completo da sessão para cópia para a área de transferência."""
        total_time = self.format_minutes_seconds(self.get_total_session_elapsed())
        avg_time = f"{self.get_average_time():.1f}s"
        total_q = len(self.questions_history)

        lines = [
            "# Relatório de Sessão - Mastering Study Quiz",
            f"- Data: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Questões Respondidas: {total_q}",
            f"- Tempo Total da Sessão: {total_time}",
            f"- Média de Tempo por Questão: {avg_time}",
            f"- Total de Tokens Consumidos: {self.total_tokens_consumed}",
            "",
            "## Histórico Detalhado por Questão",
            "| # | Tempo | Resposta | Categoria | Tokens | Latência |",
            "|---|---|---|---|---|---|"
        ]

        for q in self.questions_history:
            visual_tag = f"[{q['categoria']}]" if q["possui_visual"] else "Texto"
            lines.append(
                f"| #{q['numero']} | {q['tempo_formatado']} | {q['resposta']} | {visual_tag} | {q['tokens']} | {q['latencia_ms']}ms |"
            )

        return "\n".join(lines)

    def clear(self) -> None:
        self.session_start_time = None
        self.current_question_start_time = None
        self.is_question_active = False
        self.total_tokens_consumed = 0
        self.current_question_tokens = 0
        self.questions_history = []
