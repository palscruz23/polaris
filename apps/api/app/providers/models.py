from dataclasses import dataclass


@dataclass(frozen=True)
class AvailableModel:
    id: str
    label: str
    context_window: int
    enabled: bool = True


AVAILABLE_MODELS = (
    AvailableModel(
        id="openai/gpt-5.5",
        label="GPT-5.5 (For prod use)",
        context_window=1_050_000,
        enabled=False,
    ),
    AvailableModel(
        id="openai/gpt-5.4",
        label="GPT-5.4 (For prod use)",
        context_window=1_050_000,
        enabled=False,
    ),
    AvailableModel(
        id="openai/gpt-5.4-mini",
        label="GPT-5.4 Mini (For prod use)",
        context_window=400_000,
        enabled=False,
    ),
    AvailableModel(
        id="anthropic/claude-opus-4.8",
        label="Claude Opus 4.8 (For prod use)",
        context_window=1_000_000,
        enabled=False,
    ),
    AvailableModel(
        id="anthropic/claude-sonnet-4.6",
        label="Claude Sonnet 4.6 (For prod use)",
        context_window=1_000_000,
        enabled=False,
    ),
    AvailableModel(
        id="anthropic/claude-haiku-4.5",
        label="Claude Haiku 4.5 (For prod use)",
        context_window=200_000,
        enabled=False,
    ),
    AvailableModel(
        id="deepseek/deepseek-v4-pro",
        label="DeepSeek V4 Pro",
        context_window=1_048_576,
    ),
    AvailableModel(
        id="deepseek/deepseek-v4-flash",
        label="DeepSeek V4 Flash",
        context_window=1_048_576,
    ),
    AvailableModel(
        id="qwen/qwen3-235b-a22b-2507",
        label="Qwen3 235B",
        context_window=262_144,
    ),
    AvailableModel(
        id="google/gemma-3-12b-it",
        label="Gemma 3 12B",
        context_window=131_072,
    ),
    AvailableModel(
        id="meta-llama/llama-3.3-70b-instruct",
        label="Llama 3.3 70B",
        context_window=131_072,
    ),
)

DEFAULT_MODEL_ID = "deepseek/deepseek-v4-flash"
MODEL_BY_ID = {model.id: model for model in AVAILABLE_MODELS}


def get_available_model(model_id: str | None) -> AvailableModel:
    selected_model_id = model_id or DEFAULT_MODEL_ID

    try:
        selected_model = MODEL_BY_ID[selected_model_id]
    except KeyError as error:
        raise ValueError("The selected model is not available.") from error

    if not selected_model.enabled:
        raise ValueError("The selected model is reserved for production use.")

    return selected_model
