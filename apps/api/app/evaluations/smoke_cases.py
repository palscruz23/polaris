from app.services.evaluation_service import EvalCaseDefinition


SMOKE_SUITE_NAME = "smoke"
SMOKE_SUITE_DESCRIPTION = (
    "End-to-end Reliability Agent smoke checks for routing, intent selection, "
    "specialist execution, deterministic tool traces, and answer grounding."
)


SMOKE_CASES = (
    EvalCaseDefinition(
        name="equipment_master_search",
        prompt=(
            "Find pump equipment in the equipment master and show the most "
            "relevant identifiers."
        ),
        tags=["master_data", "routing"],
        expectations={
            "expected_tool_calls": [
                {
                    "tool": "search_equipment_master",
                    "target_agent": "master_data",
                    "required_result_terms": ["P-"],
                }
            ],
            "required_answer_terms": ["pump"],
            "required_model_call_types": [
                "agent_tool_selection",
            ],
        },
    ),
    EvalCaseDefinition(
        name="defect_elimination_bad_actors",
        prompt=(
            "Which equipment are the worst bad actors in the work order "
            "history, and what should we do next?"
        ),
        tags=["defect_elimination", "bad_actors"],
        expectations={
            "expected_tool_calls": [
                {
                    "tool": "analyze_defect_elimination",
                    "target_agent": "defect_elimination",
                    "allowed_intents": ["rank_bad_actors", "overview"],
                    "required_sub_tools": [
                        "reliability_metrics",
                        "bad_actor_analysis",
                    ],
                }
            ],
            "required_answer_terms": ["bad actor"],
            "required_model_call_types": [
                "agent_tool_selection",
                "agent_final_synthesis",
            ],
        },
    ),
    EvalCaseDefinition(
        name="maintenance_strategy_gaps",
        prompt=(
            "Review the maintenance strategy for recurring failures and "
            "identify the most important gaps."
        ),
        tags=["maintenance_strategy", "strategy_gaps"],
        expectations={
            "expected_tool_calls": [
                {
                    "tool": "review_maintenance_strategy",
                    "target_agent": "maintenance_strategy",
                    "allowed_intents": [
                        "detect_gaps",
                        "full_strategy_review",
                    ],
                    "required_sub_tools": [
                        "maintenance_strategy_profile_builder",
                        "maintenance_mix_analyzer",
                        "failure_mode_coverage_analyzer",
                    ],
                }
            ],
            "required_answer_terms": ["strategy"],
            "required_model_call_types": [
                "agent_tool_selection",
                "agent_final_synthesis",
            ],
        },
    ),
)
