# =============================================================================
# Task catalogue for the auto-rotation LLM router
# =============================================================================
# Central knowledge of which model each provider should serve for a given task
# class. Models are tuned so the strongest reasoning provider leads on
# code/security work while cheap/low-latency providers win on fast tasks.
# =============================================================================

# Task ids understood by the router. The frontend and /api/v1/llm/* endpoints
# share this vocabulary.
TASK_TYPES = [
    "code_review",     # deep reasoning over diffs / pull requests
    "code_fix",        # generate corrected code
    "security",        # vulnerability triage, CVE analysis
    "summary",         # fast, cheap summarization
    "chat",            # general conversation / assistant
    "multimodal",      # image + text understanding
    "review_comment",  # short humanised review feedback
]

TASK_LABELS = {
    "code_review": "Code Review (deep reasoning)",
    "code_fix": "Code Fix (code generation)",
    "security": "Security / CVE Analysis",
    "summary": "Summarization (fast)",
    "chat": "General Chat",
    "multimodal": "Multimodal (image+text)",
    "review_comment": "Review Comments (short)",
}

# Default base URL + auth style per provider id.
#   auth: "bearer"  -> Authorization: Bearer <key>
#         "x-goog"  -> x-goog-api-key: <key>
#         "x-api"   -> x-api-key + anthropic-version (Anthropic protocol)
#         "none"    -> local / no key needed
PROVIDER_META = {
    "nvidia": {
        "name": "NVIDIA",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "auth": "bearer",
        "multimodal": False,
        "task_models": {
            "code_review": "nvidia/llama-3.1-nemotron-70b-instruct",
            "code_fix": "nvidia/llama-3.3-70b-instruct",
            "security": "nvidia/llama-3.1-nemotron-70b-instruct",
            "summary": "nvidia/llama-3.3-70b-instruct",
            "chat": "nvidia/llama-3.3-70b-instruct",
            "review_comment": "nvidia/llama-3.3-70b-instruct",
        },
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "auth": "bearer",
        "multimodal": True,
        "task_models": {
            "code_review": "anthropic/claude-3.5-sonnet",
            "code_fix": "anthropic/claude-3.5-sonnet",
            "security": "anthropic/claude-3.5-sonnet",
            "summary": "meta-llama/llama-3.3-70b-instruct",
            "chat": "meta-llama/llama-3.3-70b-instruct",
            "multimodal": "anthropic/claude-3.5-sonnet",
            "review_comment": "meta-llama/llama-3.3-70b-instruct",
        },
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "auth": "bearer",
        "multimodal": True,
        "task_models": {
            "code_review": "gpt-4o",
            "code_fix": "gpt-4o",
            "security": "gpt-4o",
            "summary": "gpt-4o-mini",
            "chat": "gpt-4o-mini",
            "multimodal": "gpt-4o",
            "review_comment": "gpt-4o-mini",
        },
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "auth": "x-api",
        "multimodal": True,
        "task_models": {
            "code_review": "claude-3-5-sonnet-20241022",
            "code_fix": "claude-3-5-sonnet-20241022",
            "security": "claude-3-5-sonnet-20241022",
            "summary": "claude-3-5-haiku-20241022",
            "chat": "claude-3-5-sonnet-20241022",
            "multimodal": "claude-3-5-sonnet-20241022",
            "review_comment": "claude-3-5-haiku-20241022",
        },
    },
    "google": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "auth": "x-goog",
        "multimodal": True,
        "task_models": {
            "code_review": "gemini-2.0-flash",
            "code_fix": "gemini-2.0-flash",
            "security": "gemini-2.0-flash",
            "summary": "gemini-2.0-flash",
            "chat": "gemini-2.0-flash",
            "multimodal": "gemini-2.0-flash",
            "review_comment": "gemini-2.0-flash",
        },
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "auth": "bearer",
        "multimodal": False,
        "task_models": {
            "code_review": "llama-3.3-70b-versatile",
            "code_fix": "llama-3.3-70b-versatile",
            "security": "llama-3.3-70b-versatile",
            "summary": "llama-3.1-8b-instant",
            "chat": "llama-3.3-70b-versatile",
            "review_comment": "llama-3.1-8b-instant",
        },
    },
    "mistral": {
        "name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "auth": "bearer",
        "multimodal": False,
        "task_models": {
            "code_review": "mistral-large-latest",
            "code_fix": "mistral-large-latest",
            "security": "mistral-large-latest",
            "summary": "mistral-small-latest",
            "chat": "mistral-large-latest",
            "review_comment": "mistral-small-latest",
        },
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "auth": "bearer",
        "multimodal": True,
        "task_models": {
            "code_review": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "code_fix": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "security": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "summary": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "chat": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "multimodal": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "review_comment": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        },
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "auth": "bearer",
        "multimodal": False,
        "task_models": {
            "code_review": "deepseek-reasoner",
            "code_fix": "deepseek-chat",
            "security": "deepseek-reasoner",
            "summary": "deepseek-chat",
            "chat": "deepseek-chat",
            "review_comment": "deepseek-chat",
        },
    },
    "perplexity": {
        "name": "Perplexity",
        "base_url": "https://api.perplexity.ai",
        "auth": "bearer",
        "multimodal": False,
        "task_models": {
            "code_review": "sonar-pro",
            "code_fix": "sonar-pro",
            "security": "sonar-pro",
            "summary": "sonar",
            "chat": "sonar",
            "review_comment": "sonar",
        },
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434",
        "auth": "none",
        "multimodal": True,
        "task_models": {
            "code_review": "llama3.1:70b",
            "code_fix": "qwen2.5:72b",
            "security": "llama3.1:70b",
            "summary": "llama3.1:8b",
            "chat": "llama3.1:8b",
            "multimodal": "llava",
            "review_comment": "llama3.1:8b",
        },
    },
}

# Per-provider env var used as a key fallback when the admin store has none.
ENV_KEY_MAP = {
    "nvidia": "NVIDIA_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "together": "TOGETHER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "ollama": None,
}

# Primary task -> ordered fallback preference across providers. The first
# provider that is configured + healthy wins. "openrouter" acts as an
# aggregator so it doubles as a universal fallback.
TASK_ROUTING_PREFERENCE = {
    "code_review": ["nvidia", "anthropic", "openrouter", "openai", "google", "groq", "together", "mistral", "deepseek", "ollama"],
    "code_fix": ["nvidia", "openrouter", "anthropic", "openai", "google", "groq", "together", "mistral", "deepseek", "ollama"],
    "security": ["nvidia", "openrouter", "anthropic", "openai", "groq", "google", "together", "mistral", "deepseek", "ollama"],
    "summary": ["groq", "openrouter", "google", "openai", "mistral", "together", "nvidia", "perplexity", "deepseek", "ollama"],
    "chat": ["openrouter", "groq", "google", "openai", "mistral", "together", "nvidia", "perplexity", "deepseek", "ollama"],
    "multimodal": ["google", "openai", "openrouter", "anthropic", "together", "nvidia", "ollama"],
    "review_comment": ["groq", "openrouter", "google", "openai", "mistral", "together", "nvidia", "perplexity", "deepseek", "ollama"],
}

# Provider ids with a known (non-custom) profile. Custom providers added
# through the Admin UI fall back to OpenAI-compatible chat completions.
KNOWN_PROVIDER_IDS = set(PROVIDER_META)


def task_model_for(provider_id: str, task: str) -> str:
    meta = PROVIDER_META.get(provider_id, {})
    return meta.get("task_models", {}).get(task) or meta.get("task_models", {}).get("chat") or ""


def provider_name(provider_id: str) -> str:
    return PROVIDER_META.get(provider_id, {}).get("name", provider_id)