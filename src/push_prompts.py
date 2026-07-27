"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()


def build_prompt_template(prompt_data: dict) -> ChatPromptTemplate:
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_data["system_prompt"].strip()),
            ("human", prompt_data["user_prompt"].strip()),
        ]
    )

    prompt_metadata = {
        **prompt_data.get("metadata", {}),
        "description": prompt_data.get("description", ""),
        "version": prompt_data.get("version", ""),
        "prompt_name": "bug_to_user_story_v2",
    }
    setattr(prompt_template, "metadata", prompt_metadata)
    setattr(prompt_template, "tags", list(prompt_data.get("tags", [])))
    return prompt_template


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        prompt_template = build_prompt_template(prompt_data)
        try:
            hub.push(prompt_name, prompt_template, public=True)
        except TypeError:
            try:
                hub.push(prompt_name, prompt_template, is_public=True)
            except TypeError:
                hub.push(prompt_name, prompt_template)
        return True
    except Exception as e:
        print(f"❌ Erro ao publicar '{prompt_name}': {e}")
        return False


def validate_public_tenant(username: str) -> bool:
    """
    Garante que a conta atual do LangSmith tem um tenant handle compatível
    com o username configurado para publicação pública.

    Args:
        username: Username configurado no .env.

    Returns:
        True se a publicação pública for possível, False caso contrário.
    """
    try:
        client = Client()
        settings = client._get_settings()
        current_tenant = getattr(settings, "tenant_handle", None)

        if current_tenant != username:
            print("❌ O tenant atual do LangSmith não corresponde ao username configurado.")
            print(f"   Tenant atual: {current_tenant!r}")
            print(f"   Username configurado: {username!r}")
            print("\nPara publicar um prompt público, primeiro crie um handle público no LangSmith:")
            print("   https://smith.langchain.com/prompts")
            print("\nDepois faça login na mesma conta e tente novamente.")
            return False

        return True
    except Exception as e:
        print(f"❌ Não foi possível verificar o tenant atual do LangSmith: {e}")
        return False


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    if not isinstance(prompt_data, dict):
        return False, ["O conteúdo do prompt deve ser um dicionário YAML válido."]

    errors = []
    required_fields = ["description", "system_prompt", "user_prompt", "version", "tags", "techniques_applied", "metadata"]
    errors.extend([f"Campo obrigatório faltando: {field}" for field in required_fields if field not in prompt_data])

    system_prompt = str(prompt_data.get("system_prompt", "")).strip()
    user_prompt = str(prompt_data.get("user_prompt", "")).strip()
    if not system_prompt:
        errors.append("system_prompt está vazio")
    if not user_prompt:
        errors.append("user_prompt está vazio")
    if "TODO" in f"{system_prompt} {user_prompt}":
        errors.append("O prompt ainda contém TODOs")

    tags = prompt_data.get("tags", [])
    if not isinstance(tags, list) or not tags:
        errors.append("tags deve ser uma lista não vazia")
    elif not all(isinstance(tag, str) and tag.strip() for tag in tags):
        errors.append("tags deve conter apenas strings não vazias")

    techniques = prompt_data.get("techniques_applied", [])
    if not isinstance(techniques, list) or len(techniques) < 2:
        errors.append("techniques_applied deve conter pelo menos 2 técnicas")
    if not any("few-shot" in str(item).lower() or "few shot" in str(item).lower() for item in techniques):
        errors.append("Few-shot Learning é obrigatório em techniques_applied")
    if not any("few" not in str(item).lower() for item in techniques):
        errors.append("techniques_applied deve incluir ao menos uma técnica adicional além de Few-shot Learning")

    metadata = prompt_data.get("metadata", {})
    if not isinstance(metadata, dict):
        errors.append("metadata deve ser um dicionário")
    else:
        if not str(metadata.get("persona", "")).strip():
            errors.append("metadata.persona está vazio")
        if not str(metadata.get("context", metadata.get("objective", ""))).strip():
            errors.append("metadata.context ou metadata.objective deve estar preenchido")
        for field in ("audience",):
            if not str(metadata.get(field, "")).strip():
                errors.append(f"metadata.{field} está vazio")

    return len(errors) == 0, errors


def main():
    """Função principal"""
    required_vars = ["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]
    if not check_env_vars(required_vars):
        return 1

    print_section_header("Push de Prompt para LangSmith Hub")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(base_dir, "prompts", "bug_to_user_story_v2.yml")

    prompt_file = load_yaml(prompt_path)
    if not prompt_file:
        print(f"❌ Falha ao carregar o YAML do prompt: {prompt_path}")
        return 1

    if len(prompt_file) != 1:
        print("❌ O YAML deve conter exatamente um prompt no nível raiz.")
        return 1

    prompt_key, prompt_data = next(iter(prompt_file.items()))
    if prompt_key != "bug_to_user_story_v2":
        print(f"❌ Prompt raiz inesperado: {prompt_key}")
        return 1

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Validação do prompt falhou:")
        for error in errors:
            print(f"   - {error}")
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()
    prompt_name = f"{username}/bug_to_user_story_v2" if username else "bug_to_user_story_v2"

    print(f"📄 Prompt carregado: {prompt_path}")
    print(f"🚀 Publicando como: {prompt_name}")

    if not validate_public_tenant(username):
        return 1

    if push_prompt_to_langsmith(prompt_name, prompt_data):
        print(f"✅ Prompt publicado com sucesso: {prompt_name}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
