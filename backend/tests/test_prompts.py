from app.services.prompts import ChatTurn, PromptBuilder, DEFAULT_SYSTEM_PROMPT


def test_prompt_builder_includes_all_sections():
    builder = PromptBuilder(
        system_prompt="System instruction",
        answer_instructions="Answer briefly.",
    )
    prompt = builder.build_prompt(
        question="What is retrieval?",
        contexts=["Context snippet one.", "Context snippet two."],
        history=[
            ChatTurn(role="user", content="Hi!"),
            ChatTurn(role="assistant", content="Hello there."),
        ],
    )

    assert "System:\nSystem instruction" in prompt
    assert "Conversation History:\nUser: Hi!\nAssistant: Hello there." in prompt
    assert "Retrieved Context:\nContext 1:\nContext snippet one.\n\nContext 2:\nContext snippet two." in prompt
    assert "Instructions:\nAnswer briefly." in prompt
    assert "User Question:\nWhat is retrieval?" in prompt
    assert prompt.strip().endswith("Answer:")


def test_prompt_builder_defaults():
    builder = PromptBuilder()
    prompt = builder.build_prompt(question="Hello?", contexts=[])

    assert DEFAULT_SYSTEM_PROMPT in prompt
    assert "Retrieved Context" not in prompt

