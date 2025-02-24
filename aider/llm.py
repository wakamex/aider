import importlib
import os
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

AIDER_SITE_URL = "https://aider.chat"
AIDER_APP_NAME = "Aider"

os.environ["OR_SITE_URL"] = AIDER_SITE_URL
os.environ["OR_APP_NAME"] = AIDER_APP_NAME
os.environ["LITELLM_MODE"] = "PRODUCTION"

# `import litellm` takes 1.5 seconds, defer it!

VERBOSE = False


class LazyLiteLLM:
    _lazy_module = None

    def __getattr__(self, name):
        if name == "_lazy_module":
            return super()
        self._load_litellm()
        return getattr(self._lazy_module, name)

    def _load_litellm(self):
        if self._lazy_module is not None:
            return

        if VERBOSE:
            print("Loading litellm...")

        self._lazy_module = importlib.import_module("litellm")

        self._lazy_module.suppress_debug_info = True
        self._lazy_module.set_verbose = False
        self._lazy_module.drop_params = True
        self._lazy_module._logging._disable_debugging()


litellm = LazyLiteLLM()


class LLM:
    """LLM wrapper that handles model selection and API keys."""

    def generate(self, prompt):
        """Generate a response using the configured model.
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            The generated response text
        """
        try:
            # Get model from env var or config
            model = os.getenv("AIDER_TEST_MODEL", "gemini/gemini-2.0-flash-exp")

            # Get appropriate API key based on model
            api_key = None
            if "gemini" in model.lower():
                api_key = os.getenv("GEMINI_API_KEY")
            else:
                api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

            if not api_key:
                # Extract just the original text from the prompt
                original = prompt.split("Original text:")[-1].split("\n\n")[0].strip()
                return f" {original} [ ]"

            # Configure litellm with the API key
            litellm.api_key = api_key
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000  # Increase max tokens to avoid truncation
            )
            content = response.choices[0].message.content
            # Clean up any partial markdown or text
            if content.count('```') % 2 == 1:  # Unclosed code block
                content = content.split('```')[0]
            return content
        except Exception as e:
            # Fallback to original text with sparkles
            original = prompt.split("Original text:")[-1].split("\n\n")[0].strip()
            return f" {original} [ ]"


__all__ = [litellm, LLM]
