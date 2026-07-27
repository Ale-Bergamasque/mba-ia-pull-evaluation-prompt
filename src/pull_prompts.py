"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import sys
from pathlib import Path
from datetime import date
from dotenv import load_dotenv
from langchain import hub
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

def extract_text(message):
    """Extrai texto legível de diferentes formatos de prompt retornados pelo Hub."""

    if message is None:
        return ""

    for attribute in ("prompt", "message", "chat_prompt"):
        nested = getattr(message, attribute, None)
        if nested is not None:
            for nested_attribute in ("template", "text", "template_str"):
                value = getattr(nested, nested_attribute, None)
                if isinstance(value, str) and value.strip():
                    return value.strip()

    for attribute in ("template", "text", "content"):
        value = getattr(message, attribute, None)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return str(message).strip()


def pull_prompts_from_langsmith():
    """Realiza o download do prompt v1 publicado no LangSmith e salva uma representação YAML local."""

    prompt_name = "leonanluppi/bug_to_user_story_v1"
    output_path = Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v1.yml"

    try:
        print(f"🔎 Buscando prompt: {prompt_name}")

        prompt = hub.pull(prompt_name)

        system_prompt = ""
        user_prompt = ""

        messages = getattr(prompt, "messages", []) or []
        for message in messages:
            message_name = message.__class__.__name__.lower()
            message_text = extract_text(message)

            if not system_prompt and "system" in message_name:
                system_prompt = message_text
            elif not user_prompt and ("human" in message_name or "user" in message_name):
                user_prompt = message_text

        if not system_prompt:
            system_prompt = extract_text(getattr(prompt, "system_prompt", None))
        if not user_prompt:
            user_prompt = extract_text(getattr(prompt, "user_prompt", None))

        if not system_prompt:
            system_prompt = extract_text(prompt)
        if not user_prompt:
            raise ValueError(
                "Não foi possível localizar o user_prompt no prompt do LangSmith."
            )

        prompt_data = {
            "bug_to_user_story_v1": {
                "description": "Prompt para converter relatos de bugs em User Stories",
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "version": "v1",
                "created_at": date.today().isoformat(),
                "tags": ["bug-analysis", "user-story", "product-management"],
                "metadata": {
                    "source": prompt_name,
                    "hub": "LangSmith Prompt Hub",
                    "fetched_at": date.today().isoformat(),
                    "format": "yaml",
                },
            }
        }

        if save_yaml(prompt_data, str(output_path)):
            print(f"✅ Prompt salvo com sucesso em: {output_path}")
            return True

        print(f"❌ Não foi possível salvar o prompt em: {output_path}")
        return False
    except Exception as e:
        print(f"❌ Erro ao fazer pull do prompt '{prompt_name}': {e}")
        return False


def main():
    """Função principal"""

    print_section_header("Pull de Prompt do LangSmith Hub")

    required_vars = ["LANGSMITH_API_KEY", "LANGSMITH_ENDPOINT"]
    if not check_env_vars(required_vars):
        return 1

    try:
        success = pull_prompts_from_langsmith()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Erro inesperado na execução: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
