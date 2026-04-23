import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from storage.knowledge_indexer import KnowledgeIndexer
from storage.metadata_extractor import MetadataExtractor
from storage.wiki_link_parser import WikiLinkParser
from storage.vector_store import VectorStore
from storage.goal_store import GoalStore
from storage.decision_log import DecisionLog
from rules.rule_injector import RuleInjector
from pipeline.call1_relevance import Call1Relevance
from pipeline.call2_embed import Call2Embed
from pipeline.call3_analysis import Call3Analysis
from agents.email_agent import EmailAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.reply_agent import ReplyAgent
from agents.goal_agent import GoalAgent
from agents.daemon import Daemon
from harness.observer import Observer
from harness.evaluator import Evaluator
from harness.intervener import Intervener


BASE_DIR = Path(__file__).parent


def initialize_system():
    kb_path = BASE_DIR / os.getenv("KNOWLEDGE_BASE_PATH", "knowledge-base")
    storage_dir = BASE_DIR / "storage"
    storage_dir.mkdir(exist_ok=True)

    extractor = MetadataExtractor()
    indexer = KnowledgeIndexer(
        db_path=str(storage_dir / "knowledge_index.sqlite"),
        knowledge_base_path=str(kb_path),
    )
    wiki_parser = WikiLinkParser(db_path=str(storage_dir / "knowledge_index.sqlite"))

    print("Indexing knowledge base...")
    count = indexer.index_all(extractor)
    print(f"Indexed {count} files")

    valid_files = set(indexer.get_all_file_names())
    for md_file in kb_path.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            wiki_parser.parse_file(md_file, content, valid_files)
        except Exception:
            pass

    link_stats = wiki_parser.get_link_graph_stats()
    print(f"Wiki-links: {link_stats['total_links']} total, {link_stats['broken_links']} broken")

    rule_injector = RuleInjector(
        rules_path=str(BASE_DIR / "rules" / "rules.json"),
    )
    print(f"Rules loaded: {rule_injector.get_stats()['total']}")

    goal_store = GoalStore(goals_path=str(BASE_DIR / "goals" / "goals.json"))
    print(f"Goals loaded: {len(goal_store.get_all_goals())}")

    vector_store = VectorStore(db_path=str(storage_dir / "vector_store.sqlite"))

    observer = Observer(log_path=str(BASE_DIR / "logs" / "observations"))
    evaluator = Evaluator()
    decision_log = DecisionLog(log_path=str(BASE_DIR / "logs" / "decisions"))
    intervener = Intervener(observer=observer, evaluator=evaluator, decision_log=decision_log)

    rule_injector.observer = observer

    api_key = os.getenv("SILRA_API_KEY", "")
    api_base = os.getenv("SILRA_API_BASE_URL", "https://api.silra.cn/v1")
    api_client = None
    if api_key and not api_key.startswith("<"):
        try:
            from openai import OpenAI
            api_client = OpenAI(api_key=api_key, base_url=api_base, timeout=120)
            print(f"Silra API configured: {api_base}")
        except ImportError:
            print("WARNING: openai package not installed, using mock mode")

    call1 = Call1Relevance(indexer=indexer, rule_injector=rule_injector, api_client=api_client)
    call2 = Call2Embed(rule_injector=rule_injector, api_client=api_client)
    call3 = Call3Analysis(rule_injector=rule_injector, vector_store=vector_store, api_client=api_client)

    email_agent = EmailAgent(
        call1=call1, call2=call2, call3=call3,
        vector_store=vector_store, wiki_parser=wiki_parser,
        observer=observer,
    )

    knowledge_agent = KnowledgeAgent(
        indexer=indexer, wiki_parser=wiki_parser,
        extractor=extractor, knowledge_base_path=str(kb_path),
        observer=observer,
    )

    reply_agent = ReplyAgent(observer=observer, rule_injector=rule_injector)

    goal_agent = GoalAgent(goal_store=goal_store, observer=observer)

    daemon = Daemon(
        agents={
            "email_agent": email_agent,
            "knowledge_agent": knowledge_agent,
            "reply_agent": reply_agent,
            "goal_agent": goal_agent,
        },
        goal_agent=goal_agent,
        observer=observer,
    )

    stats = indexer.get_stats()
    print(f"\nSystem initialized:")
    print(f"  Knowledge base: {stats['total_files']} files")
    print(f"  Avg authority: {stats['avg_authority']}")
    print(f"  Avg freshness: {stats['avg_freshness']}")
    print(f"  Conflicts: {stats['conflicts']}")

    return {
        "indexer": indexer,
        "wiki_parser": wiki_parser,
        "rule_injector": rule_injector,
        "goal_store": goal_store,
        "vector_store": vector_store,
        "observer": observer,
        "evaluator": evaluator,
        "decision_log": decision_log,
        "intervener": intervener,
        "email_agent": email_agent,
        "knowledge_agent": knowledge_agent,
        "reply_agent": reply_agent,
        "goal_agent": goal_agent,
        "daemon": daemon,
    }


if __name__ == "__main__":
    system = initialize_system()

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "tick":
            result = system["daemon"].tick()
            print(f"Tick #{result.tick_number}: {result.events_found} events, {result.tasks_dispatched} dispatched")
        elif command == "health":
            report = system["observer"].get_loop_health_report()
            print(json.dumps(report, indent=2, ensure_ascii=False))
        elif command == "stats":
            print(json.dumps(system["indexer"].get_stats(), indent=2))
            print(json.dumps(system["rule_injector"].get_stats(), indent=2))
        elif command == "webui":
            from webui.app import run_server
            run_server(intervener=system["intervener"])
        else:
            print(f"Unknown command: {command}")
            print("Usage: python main.py [tick|health|stats|webui]")
    else:
        print("System initialized. Run 'python main.py tick' to process a tick.")
