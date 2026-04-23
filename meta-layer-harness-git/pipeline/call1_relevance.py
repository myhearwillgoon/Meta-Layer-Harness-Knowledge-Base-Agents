import os
import json
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class Call1Result:
    top_files: list[str]
    routing_decision: str
    confidence: float
    model_used: str
    token_usage: dict

    def to_dict(self):
        return asdict(self)


class Call1Relevance:
    SYSTEM_PROMPT = """You are a relevance judgment engine. Given an email and a list of knowledge base file names, identify the top 3 most relevant files.

Output JSON format:
{
  "top_files": ["file1.md", "file2.md", "file3.md"],
  "routing": "routine" or "complex",
  "reasoning": "brief explanation"
}

Use "complex" routing for: regulatory matters, multi-party communications, negotiations, compliance issues.
Use "routine" for: status updates, simple queries, informational emails."""

    def __init__(self, indexer, rule_injector=None, api_client=None):
        self.indexer = indexer
        self.rule_injector = rule_injector
        self.api_client = api_client
        self.model = os.getenv("CALL1_MODEL", "silra/glm-4.5")

    def execute(self, email_content: str) -> Call1Result:
        file_names = self.indexer.get_all_file_names()
        prompt = self._build_prompt(email_content, file_names)

        if self.rule_injector:
            prompt = self.rule_injector.inject(prompt, "email.call1", {"trigger": "relevance_judgment"})

        if self.api_client:
            try:
                response = self.api_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=500,
                )
                result_json = json.loads(response.choices[0].message.content)
                return Call1Result(
                    top_files=result_json.get("top_files", [])[:3],
                    routing_decision=result_json.get("routing", "routine"),
                    confidence=0.85,
                    model_used=self.model,
                    token_usage={
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                    },
                )
            except Exception:
                pass

        return self._mock_execute(email_content, file_names)

    def _build_prompt(self, email_content: str, file_names: list[str]) -> str:
        files_str = "\n".join(f"- {f}" for f in file_names)
        return f"""Knowledge Base Files:
{files_str}

Email Content:
{email_content}

Identify the top 3 most relevant files and determine routing."""

    def _mock_execute(self, email_content: str, file_names: list[str]) -> Call1Result:
        import re
        email_lower = email_content.lower()
        scored = []
        for f in file_names:
            score = 0
            f_lower = f.lower().replace("-", " ").replace("_", " ")
            for word in re.findall(r"\b\w{4,}\b", email_lower):
                if word in f_lower:
                    score += 1
            scored.append((f, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        top_files = [f for f, _ in scored[:3]]

        is_complex = any(w in email_lower for w in ["regulatory", "compliance", "negotiation", "legal", "audit"])
        return Call1Result(
            top_files=top_files,
            routing_decision="complex" if is_complex else "routine",
            confidence=0.7,
            model_used=self.model,
            token_usage={"input": len(file_names) * 8, "output": 100},
        )
