"""Language model providers.

OpenAI and Anthropic APIs are paid per call, so this is a stub for now. When
the team picks a provider, implement generate() for it here and read the API
key from an environment variable (never commit keys).
"""


class LLMProvider:
    def generate(self, system, prompt):
        raise NotImplementedError


def get_llm():
    raise NotImplementedError
