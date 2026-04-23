from dataclasses import dataclass, asdict
from pipeline.call1_relevance import Call1Relevance, Call1Result
from pipeline.call2_embed import Call2Embed, Call2Result
from pipeline.call3_analysis import Call3Analysis, Call3Result
from storage.vector_store import VectorStore
from storage.wiki_link_parser import WikiLinkParser


@dataclass
class EmailResult:
    analysis: str
    draft_reply: str
    knowledge_updates: list[dict]
    fact_check: list[dict]
    model_used: str
    top_files: list[str]
    routing_decision: str
    search_queries: list[str]
    token_usage: dict

    def to_dict(self):
        return asdict(self)


class EmailAgent:
    def __init__(self, call1: Call1Relevance, call2: Call2Embed, call3: Call3Analysis,
                 vector_store: VectorStore, wiki_parser: WikiLinkParser, observer=None):
        self.call1 = call1
        self.call2 = call2
        self.call3 = call3
        self.vector_store = vector_store
        self.wiki_parser = wiki_parser
        self.observer = observer

    def process_email(self, email_content: str) -> EmailResult:
        call1_result = self.call1.execute(email_content)

        if self.observer:
            self.observer.record_prompt_assembly(
                stage="call1",
                model=call1_result.model_used,
                token_usage=call1_result.token_usage,
            )

        expanded_context = self._expand_backlinks(call1_result.top_files)

        call2_result = self.call2.execute(email_content, expanded_context)

        if self.observer:
            self.observer.record_prompt_assembly(
                stage="call2",
                model=call2_result.model_used,
                token_usage=call2_result.token_usage,
            )

        vector_results = self._vector_search(call2_result.queries)

        full_context = expanded_context + [r.get("content_preview", "") for r in vector_results]

        call3_result = self.call3.execute(
            email_content=email_content,
            context=full_context,
            is_complex=(call1_result.routing_decision == "complex"),
        )

        if self.observer:
            self.observer.record_prompt_assembly(
                stage="call3",
                model=call3_result.model_used,
                token_usage=call3_result.token_usage,
            )

        return EmailResult(
            analysis=call3_result.analysis,
            draft_reply=call3_result.draft_reply,
            knowledge_updates=call3_result.knowledge_updates,
            fact_check=call3_result.fact_check,
            model_used=call3_result.model_used,
            top_files=call1_result.top_files,
            routing_decision=call1_result.routing_decision,
            search_queries=call2_result.queries,
            token_usage={
                "call1": call1_result.token_usage,
                "call2": call2_result.token_usage,
                "call3": call3_result.token_usage,
            },
        )

    def _expand_backlinks(self, top_files: list[str]) -> list[str]:
        valid_files = set(self.call1.indexer.get_all_file_names())
        expanded = self.wiki_parser.expand_with_backlinks(top_files, valid_files, max_links=30)
        return list(expanded)

    def _vector_search(self, queries: list[str]) -> list[dict]:
        mock_embeddings = [[0.1] * 128, [0.2] * 128]
        return self.vector_store.search_multi(mock_embeddings, limit_per_query=30)
