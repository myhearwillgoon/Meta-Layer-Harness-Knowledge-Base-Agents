# API Documentation

## Agent API

### EmailAgent

```python
email_agent = EmailAgent(call1, call2, call3, vector_store, wiki_parser, observer)
result = email_agent.process_email(email_content: str) -> EmailResult
```

**EmailResult fields:**
- `analysis`: str — Analysis of the email
- `draft_reply`: str — Draft response
- `knowledge_updates`: list[dict] — Suggested KB updates
- `fact_check`: list[dict] — Claims needing verification
- `model_used`: str — Model used for Call #3
- `top_files`: list[str] — Top 3 relevant KB files
- `routing_decision`: str — "routine" or "complex"
- `search_queries`: list[str] — 2 generated search queries
- `token_usage`: dict — Token usage per call

### KnowledgeAgent

```python
knowledge_agent = KnowledgeAgent(indexer, wiki_parser, extractor, kb_path, observer)
knowledge_agent.append_entry(title, content, category) -> dict
knowledge_agent.create_entry(title, content, category) -> dict  # Requires approval
knowledge_agent.get_entry(file_path) -> dict
knowledge_agent.search_entries(query) -> list[dict]
```

### ReplyAgent

```python
reply_agent = ReplyAgent(observer, rule_injector)
draft = reply_agent.generate_draft(analysis, email_content, style) -> dict
correction = reply_agent.capture_user_correction(draft_id, user_edit) -> dict
```

### GoalAgent

```python
goal_agent = GoalAgent(goal_store, observer)
result = goal_agent.complete_leaf_goal(goal_id) -> dict
review = goal_agent.review_goal(goal_id) -> dict
tree = goal_agent.get_goal_tree(root_id) -> dict
```

### Daemon

```python
daemon = Daemon(agents, goal_agent, observer)
result = daemon.tick() -> TickResult
daemon.run_loop(max_ticks=None)  # Blocking loop
daemon.stop()
daemon.add_event({"type": "email", "content": "...", "priority": "normal"})
```

## Pipeline API

### Call #1 — Relevance Judgment

```python
call1 = Call1Relevance(indexer, rule_injector, api_client)
result = call1.execute(email_content) -> Call1Result
```

### Call #2 — Embed Query Generation

```python
call2 = Call2Embed(rule_injector, api_client)
result = call2.execute(email_content, top_files_context) -> Call2Result
```

### Call #3 — Analysis

```python
call3 = Call3Analysis(rule_injector, vector_store, api_client)
result = call3.execute(email_content, context, is_complex=False) -> Call3Result
```

## Meta Layer API

### Observer

```python
observer = Observer(log_path="logs/observations/")
observer.record_knowledge_metadata(file_path, metadata)
observer.record_prompt_assembly(stage, model, token_usage, sources, rules_injected)
observer.record_rule_injection(injection_point, rules_injected, reason, impact)
observer.record_loop_health(metrics)
observer.record_user_correction(draft_id, original, user_edit, diff)
report = observer.get_loop_health_report() -> dict
```

### Evaluator

```python
evaluator = Evaluator(numerical_threshold=0.05)
conflict = evaluator.detect_numerical_conflict(source_a, source_b, metric)
conflict = evaluator.detect_semantic_conflict(statement_a, statement_b)
confidence = evaluator.calculate_confidence(authority, freshness, consistency, query_type)
impact = evaluator.analyze_impact(change_type, target_id, reference_graph)
```

### Intervener

```python
intervener = Intervener(observer, evaluator, decision_log)
marker = intervener.mark_output(confidence_score, conflicts, source_meta)
formatted = intervener.format_output(content, marker)
is_open = intervener.check_circuit_breaker(health_report)
intervener.add_to_audit_queue(request_id, risk_level, action_type, description)
intervener.approve_audit_item(request_id, reviewer)
```

## CLI Commands

```bash
python main.py tick       # Run one daemon tick
python main.py health     # Get loop health report
python main.py stats      # Get system stats
python main.py webui      # Start HITL Web UI (port 8080)
```
