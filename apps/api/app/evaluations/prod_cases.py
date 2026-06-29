from app.services.evaluation_service import EvalCaseDefinition


PROD_SUITE_NAME = "prod"
PROD_SUITE_DESCRIPTION = (
    "Production-style end-to-end Reliability Agent checks for realistic "
    "query and answer quality across bad actors, repeat failures, maintenance "
    "strategy gaps, and master-data lookups."
)


PROD_CASES = (
    EvalCaseDefinition(
        name="prod_bad_actor_prioritization",
        prompt=(
            "Our maintenance team needs tomorrow's reliability focus list. "
            "Identify the worst equipment bad actors from the work order "
            "history, explain the evidence, and recommend the next action."
        ),
        tags=["prod", "defect_elimination", "bad_actors"],
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
            "required_answer_terms": [
                "bad actor",
                "work order",
                "recommend",
            ],
            "required_model_call_types": [
                "agent_tool_selection",
                "agent_final_synthesis",
            ],
        },
    ),
    EvalCaseDefinition(
        name="prod_repeat_failure_investigation",
        prompt=(
            "Find repeated failure patterns in the production work order "
            "history and tell me which equipment should get a formal defect "
            "elimination investigation first."
        ),
        tags=["prod", "defect_elimination", "repeat_failures"],
        expectations={
            "expected_tool_calls": [
                {
                    "tool": "analyze_defect_elimination",
                    "target_agent": "defect_elimination",
                    "allowed_intents": [
                        "find_repeat_failures",
                        "overview",
                    ],
                    "required_sub_tools": [
                        "reliability_metrics",
                        "repeat_failure_detection",
                    ],
                }
            ],
            "required_answer_terms": [
                "repeat",
                "failure",
                "investigation",
            ],
            "required_model_call_types": [
                "agent_tool_selection",
                "agent_final_synthesis",
            ],
        },
    ),
    EvalCaseDefinition(
        name="prod_strategy_gap_review",
        prompt=(
            "Review whether our current maintenance strategies cover the "
            "failure modes showing up in work orders. Highlight the highest "
            "risk coverage gaps and what strategy changes are needed."
        ),
        tags=["prod", "maintenance_strategy", "strategy_gaps"],
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
            "required_answer_terms": [
                "strategy",
                "gap",
                "failure mode",
            ],
            "required_model_call_types": [
                "agent_tool_selection",
                "agent_final_synthesis",
            ],
        },
    ),
    EvalCaseDefinition(
        name="prod_equipment_context_lookup",
        prompt=(
            "Before we plan work, find the available pump equipment records "
            "and summarize the identifiers, locations, and criticality context "
            "that should shape prioritization."
        ),
        tags=["prod", "master_data", "equipment"],
        expectations={
            "expected_tool_calls": [
                {
                    "tool": "search_equipment_master",
                    "target_agent": "master_data",
                    "required_result_terms": ["P-"],
                }
            ],
            "required_answer_terms": [
                "pump",
                "criticality",
            ],
            "required_model_call_types": [
                "agent_tool_selection",
            ],
        },
    ),
)
