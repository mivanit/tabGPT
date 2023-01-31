# TODO: this is for an old version and no longer works -- some jax dependency issues? need to fix

import json
import typing

import torch
from transformers import (AutoModelForCausalLM,  # type: ignore[import]
                          AutoTokenizer)

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
    """Generate continuation text for a given prompt using a pre-trained LLM.

    Args:
        prompt (str): The prompt to generate text continuation from.
        max_length (int, optional): The maximum length of the generated text.
          Defaults to 5.
        stop_token (str, optional): The token to stop generating text at.
          Defaults to None.

    Returns:
        str: The generated text continuation for the prompt.

    Example:
        >>> generate_continuation("The sky is", max_length=10, stop_token=".")
        'The sky is blue.'
    """
    input_ids: torch.Tensor = TOKENIZER.encode(prompt, return_tensors="pt")
    generated_text_ids = MODEL.generate(
        input_ids=input_ids.to(device),
        max_length=max_length + len(input_ids[0]),
        do_sample=False,
    )
    generated_text: str = TOKENIZER.decode(
        generated_text_ids[0], clean_up_tokenization_spaces=True
    )
    prompt_stripped = TOKENIZER.decode(input_ids[0], clean_up_tokenization_spaces=True)
    post_prompt_text: str = generated_text[len(prompt_stripped) :]

    stop_index = post_prompt_text.find(stop_token) + 1 if stop_token else None
    return post_prompt_text[:stop_index]


def generate(prompt: str, max_length: int = 5, stop_token: str | None = None) -> str:
    return prompt + generate_continuation(prompt, max_length, stop_token)


def get_logits_and_tokens(text: str):
    """Get the logits and tokens for a given input text.

    Args:
        text (str): The input text.

    Returns:
        Tuple of (logits, tokens) for the input text.

        logits (torch.Tensor): A tensor of logits for the input text, of shape
          (x, y), where x is the number of logits and y is the size of the
          vocab. The logit for the final token is ommitted (TODO: why?).
        tokens (List[str]): A list of tokens for the input text.

    Example:
        >>> get_logits_and_tokens("hello, world!")
        (tensor([[-34.7599, -32.6039, -34.7921,  ..., -46.8525, -46.5174, -35.0202],
            [-64.8099, -62.6199, -63.4192,  ..., -69.6624, -67.5905, -62.8190],
            [-51.3938, -51.6655, -51.3386,  ..., -61.4105, -58.3002, -52.3297]],
            grad_fn=<SliceBackward0>), ['hello', ',', ' world', '!'])
    """

    input_ids: torch.Tensor = TOKENIZER.encode(text, return_tensors="pt")
    tokens: list[str] = [TOKENIZER.decode([input_id]) for input_id in input_ids[0]]
    output = MODEL(input_ids.to(device))
    return output.logits[0][:-1], tokens


def test_generation(
    EXAMPLE_PROMPT: str = """Horrible: negative\nGreat: positive\nBad:""",
    max_length: int = 5,
    stop_token: str = "\n",
):
    """Generate a continuation based on the EXAMPLE_PROMPT.

    Print the following to stdout:
      * The prompt plus continuation, up to [max_length] or [stop_token],
        whichever comes first.
      * The probability that the last token equals " negative".
      * The probabiilty that the last token equals " positive".

    Example:
        >>> generate_tokens(
                \"\"\"Horrible: negative\nGreat: positive\nBad:\"\"\",
                max_length=5,
                stop_token="\n"
        )
        tokens: ['Hor', 'rible', ':', ' negative', '\n', 'Great', ':',
          ' positive', '\n', 'Bad', ':', ' negative', '\n']
        negative prob: 0.00023237711866386235
        positive prob: 7.43172422517091e-05
    """
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

    print(f"tokens: {tokens}")
    print(f"negative prob: {negative_prob}")
    print(f"positive prob: {positive_prob}")


def test_generation_from_file(
    filename: str = "prompt.txt",
    max_length: int = 10,
    stop_token: str = "\n",
):
    """Generate a continuation based on a prompt in a file."""
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
