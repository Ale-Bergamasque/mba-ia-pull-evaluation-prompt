"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
from pathlib import Path

from src.utils import validate_prompt_structure


PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"

def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

class TestPrompts:
    def _get_prompt_data(self):
        prompts = load_prompts(str(PROMPT_FILE))
        assert isinstance(prompts, dict), "Arquivo YAML inválido ou vazio"
        assert PROMPT_KEY in prompts, f"Prompt '{PROMPT_KEY}' não encontrado"
        return prompts[PROMPT_KEY]

    def test_prompt_has_system_prompt(self):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        prompt = self._get_prompt_data()
        system_prompt = str(prompt.get("system_prompt", "")).strip()
        assert system_prompt, "system_prompt deve existir e não pode estar vazio"

    def test_prompt_has_role_definition(self):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        prompt = self._get_prompt_data()
        system_prompt = str(prompt.get("system_prompt", "")).lower()
        metadata = prompt.get("metadata", {})
        persona = str(metadata.get("persona", "")).strip()

        has_role_in_text = "product manager" in system_prompt
        has_role_metadata = bool(persona)
        assert has_role_in_text or has_role_metadata, "Prompt deve definir persona/role"

    def test_prompt_mentions_format(self):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        prompt = self._get_prompt_data()
        full_text = (
            f"{prompt.get('system_prompt', '')}\n"
            f"{prompt.get('user_prompt', '')}\n"
            f"{prompt.get('format', '')}"
        ).lower()

        assert "markdown" in full_text, "Prompt deve mencionar formato Markdown"
        assert "user story" in full_text, "Prompt deve mencionar User Story"

    def test_prompt_has_few_shot_examples(self):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        prompt = self._get_prompt_data()
        system_prompt = str(prompt.get("system_prompt", "")).lower()
        techniques = [str(t).lower() for t in prompt.get("techniques_applied", [])]
        tags = [str(t).lower() for t in prompt.get("tags", [])]

        has_few_shot_marker = any("few-shot" in t or "few shot" in t for t in techniques + tags)
        has_examples = ("input:" in system_prompt and "output:" in system_prompt) or "exemplo" in system_prompt

        assert has_few_shot_marker, "Few-shot deve estar declarado em techniques_applied ou tags"
        assert has_examples, "Prompt deve conter exemplos de entrada/saída"

    def test_prompt_no_todos(self):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        prompt = self._get_prompt_data()
        prompt_text = yaml.safe_dump(prompt, allow_unicode=True).lower()
        assert "[todo]" not in prompt_text, "Prompt não deve conter [TODO]"

    def test_minimum_techniques(self):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        prompt = self._get_prompt_data()
        techniques = prompt.get("techniques_applied", [])

        assert isinstance(techniques, list), "techniques_applied deve ser uma lista"
        assert len(techniques) >= 2, "Prompt deve listar pelo menos 2 técnicas"

        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, f"Estrutura básica do prompt inválida: {errors}"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])