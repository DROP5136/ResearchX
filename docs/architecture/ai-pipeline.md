# AI pipeline

The LangGraph workflow in `apps/ai-service/app/graph/workflow.py` orchestrates:

1. **Planner** — subtasks / research plan  
2. **Researcher** — web search + source collection  
3. **Extractor** — claims / evidence  
4. **Fact checker** — verification + contradictions  
5. **Analyst** — quantitative analysis + charts  
6. **Writer** — final markdown/JSON report  

Providers (LLM/search) are swappable via `apps/ai-service/app/providers`. Outputs land under `data/outputs/<research_id>/`. Evaluation lives in `app/evaluation` with benchmarks under repo `evaluation/benchmarks/`.
