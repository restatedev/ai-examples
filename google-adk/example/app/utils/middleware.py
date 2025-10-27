from typing import AsyncGenerator

import restate
from google.adk.models.base_llm import BaseLlm
from google.adk.models import LlmRequest, LlmResponse, LLMRegistry

def durable_model_calls(ctx: restate.Context, model: str | BaseLlm):

    # If a model name is provided, create an instance of the model
    if isinstance(model, str):
      model = LLMRegistry.new_llm(model)

    class RestateModel(type(model)):
        """A simple model that restates the prompt."""

        async def generate_content_async(self,
                                 llm_request: 'LlmRequest',
                                 stream: bool = False) -> AsyncGenerator['LlmResponse', None]:

            if stream:
                raise restate.TerminalError(
                    "Streaming is not supported in Restate. Set StreamingMode to NONE."
                )

            async def call_llm() -> LlmResponse:
                # Without streaming the generator will yield only one response
                a_gen = model.generate_content_async(llm_request, stream=False)
                return await anext(a_gen)

            yield await ctx.run_typed(
                "call LLM", call_llm, restate.RunOptions(max_attempts=3)
            )

    # Copy the model's attributes to create an instance with the same configuration
    return RestateModel(**model.__dict__)