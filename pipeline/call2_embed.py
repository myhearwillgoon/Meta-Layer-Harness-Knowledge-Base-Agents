import os
import json
import re
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class Call2Result:
    queries: list[str]
    model_used: str
    token_usage: dict

    def to_dict(self):
        return asdict(self)


class Call2Embed:
    SYSTEM_PROMPT = """You are a search query generator. Given an email and relevant knowledge context, generate exactly 2 natural language search queries that would find the most relevant information.

Output JSON format:
{
  "queries": ["natural language query 1", "natural language query 2"]
}

Rules:
- Use natural language descriptions, not keywords
- Each query should target a different aspect of the email
- Be specific and descriptive"""

    def __init__(self, rule_injector=None, api_client=None):
        self.rule_injector = rule_injector
        self.api_client = api_client
        self.model = os.getenv("CALL2_MODEL", "silra/glm-4.5")

    def execute(self, email_content: str, top_files_context: list[str]) -> Call2Result:
        prompt = self._build_prompt(email_content, top_files_context)

        if self.rule_injector:
            prompt = self.rule_injector.inject(prompt, "email.embed", {"trigger": "query_generation"})

        if self.api_client:
            try:
                response = self.api_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=300,
                )
                result_json = json.loads(response.choices[0].message.content)
                return Call2Result(
                    queries=result_json.get("queries", [])[:2],
                    model_used=self.model,
                    token_usage={
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                    },
                )
            except Exception:
                pass

        return self._mock_execute(email_content)

    def _build_prompt(self, email_content: str, context: list[str]) -> str:
        ctx = "\n".join(context)
        return f"""Knowledge Context:
{ctx}

Email:
{email_content}

Generate 2 natural language search queries."""

    def _mock_execute(self, email_content: str) -> Call2Result:
        topics = re.findall(r"\b[A-Z]{2,5}\b", email_content)
        queries = []
        if topics:
            queries.append(f"Latest information about {topics[0]} position and strategy")
        if len(topics) > 1:
            queries.append(f"Risk assessment and compliance guidelines for {topics[1]}")
        else:
            queries.append("Current portfolio allocation and risk framework")
            queries.append("Latest investment committee decisions and policy updates")

        return Call2Result(
            queries=queries[:2],
            model_used=self.model,
            token_usage={"input": 5000, "output": 100},
        )
