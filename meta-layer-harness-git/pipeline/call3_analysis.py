import os
import json
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class Call3Result:
    analysis: str
    draft_reply: str
    knowledge_updates: list[dict]
    fact_check: list[dict]
    model_used: str
    confidence: float
    token_usage: dict

    def to_dict(self):
        return asdict(self)


class Call3Analysis:
    SYSTEM_PROMPT = """You are an AI operations analyst. Analyze the email and output JSON:
{
  "analysis": "2-3 sentence analysis",
  "draft_reply": "brief professional reply",
  "knowledge_updates": [],
  "fact_check": []
}"""

    def __init__(self, rule_injector=None, vector_store=None, api_client=None):
        self.rule_injector = rule_injector
        self.vector_store = vector_store
        self.api_client = api_client
        self.complex_model = os.getenv("CALL3_COMPLEX_MODEL", "glm-4.5-air")
        self.routine_model = os.getenv("CALL3_ROUTINE_MODEL", "glm-4.5-air")

    def execute(self, email_content: str, context: list[str], is_complex: bool = False) -> Call3Result:
        model = self.complex_model if is_complex else self.routine_model
        prompt = self._build_prompt(email_content, context[:5])  # Limit to top 5 contexts

        if self.rule_injector:
            prompt = self.rule_injector.inject(prompt, "email.analysis", {"trigger": "analysis"})

        if self.api_client:
            try:
                response = self.api_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=800,
                )
                content = response.choices[0].message.content.strip()
                
                # Handle markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].strip()
                
                result_json = json.loads(content)
                return Call3Result(
                    analysis=result_json.get("analysis", ""),
                    draft_reply=result_json.get("draft_reply", ""),
                    knowledge_updates=result_json.get("knowledge_updates", []),
                    fact_check=result_json.get("fact_check", []),
                    model_used=model,
                    confidence=0.9,
                    token_usage={
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                    },
                )
            except Exception as e:
                print(f"[WARN] Call #3 API failed: {e}")
                pass

        return self._mock_execute(email_content, context, is_complex)

    def _build_prompt(self, email_content: str, context: list[str]) -> str:
        ctx = "\n".join(context)[:5000]  # Truncate context to 5k chars
        return f"Context:\n{ctx}\n\nEmail:\n{email_content[:2000]}\n\nRespond with JSON only."

    def _mock_execute(self, email_content: str, context: list[str], is_complex: bool) -> Call3Result:
        model = self.complex_model if is_complex else self.routine_model
        return Call3Result(
            analysis=f"[MOCK] Analysis using {model}. Context: {len(context)} files.",
            draft_reply="[MOCK] Thank you for your email.",
            knowledge_updates=[],
            fact_check=[],
            model_used=model,
            confidence=0.7,
            token_usage={"input": 50000, "output": 2000},
        )
