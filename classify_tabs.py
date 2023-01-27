# TODO: this is for an old version and no longer works -- some jax dependency issues? need to fix

import typing
import json

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM  # type: ignore[import]

# pylint: disable=missing-class-docstring,missing-function-docstring,dangerous-default-value
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# load model as global variable
# ==============================
TOKENIZER: AutoTokenizer
MODEL: AutoModelForCausalLM
if not typing.TYPE_CHECKING:
    # dont load the model if we are just type checking
    # TOKENIZER = GPT2Tokenizer.from_pretrained('gpt2')
    # TOKENIZER.pad_token = TOKENIZER.eos_token
    # MODEL = GPT2LMHeadModel.from_pretrained('gpt2', pad_token_id=TOKENIZER.eos_token_id)
    # MODEL.eval().to(device)
    # tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
    # model = AutoModelForCausalLM.from_pretrained("distilgpt2")

    TOKENIZER = AutoTokenizer.from_pretrained("distilgpt2")
    MODEL = AutoModelForCausalLM.from_pretrained("distilgpt2")


# helper functions
# ==============================
def generate_continuation(
    prompt: str, max_length: int = 5, stop_token: str | None = None
) -> str:
    input_ids: torch.Tensor = TOKENIZER.encode(prompt, return_tensors="pt")
    generated_text_ids = MODEL.generate(
        input_ids=input_ids.to(device),
        max_length=max_length + len(input_ids[0]),
        do_sample=False,
    )
    generated_text: str = TOKENIZER.decode(
        generated_text_ids[0], clean_up_tokenization_spaces=True
    )
    post_prompt_text: str = generated_text[
        len(TOKENIZER.decode(input_ids[0], clean_up_tokenization_spaces=True)) :
    ]
    return post_prompt_text[: post_prompt_text.find(stop_token) if stop_token else None]


def generate(prompt: str, max_length: int = 5, stop_token: str | None = None) -> str:
    return prompt + generate_continuation(prompt, max_length, stop_token)


def get_logits_and_tokens(text: str):
    input_ids: torch.Tensor = TOKENIZER.encode(text, return_tensors="pt")
    tokens: list[str] = [TOKENIZER.decode([input_id]) for input_id in input_ids[0]]
    output = MODEL(input_ids.to(device))
    return output.logits[0][:-1], tokens


def test_generation(
    EXAMPLE_PROMPT: str = """Horrible: negative\nGreat: positive\nBad:""",
    max_length: int = 5,
    stop_token: str = "\n",
):
    example_gen: str = generate(
        EXAMPLE_PROMPT,
        max_length=max_length,
        stop_token=stop_token,
    )

    print(example_gen)

    logits, tokens = get_logits_and_tokens(example_gen)
    last_token_probs = torch.softmax(logits[-1], dim=0)
    negative_prob = last_token_probs[TOKENIZER.encode(" negative")[0]]
    positive_prob = last_token_probs[TOKENIZER.encode(" positive")[0]]

    print(
        f"tokens: {tokens}\nnegative prob: {negative_prob}\npositive prob: {positive_prob}"
    )


def test_generation_from_file(
        filename: str = "temp.txt", 
        max_length: int = 10, 
        stop_token: str = "\n",
    ):
    with open(filename, "r") as f:
        prompt: str = f.read()

    test_generation(prompt, max_length=max_length, stop_token=stop_token)


if __name__ == "__main__":
    import fire  # type: ignore[import]

    fire.Fire(
        dict(
            gen=test_generation,
            gen_file=test_generation_from_file,
        )
    )
