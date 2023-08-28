from aws_cdk import App, Stack, Tags
from modules.config import config


class GenAiStack(Stack):
    def __init__(self, app: App, id: str, stack, **kwargs) -> None:
        # ------------------------------------------------------------------------------
        # Call parent AWS Stack constructor with enhanced name and save the original id
        # ------------------------------------------------------------------------------
        super().__init__(
            app,
            config["code"] + config["appPrefix"] + id,
            description=stack["description"],
            **kwargs
        )
        self.original_id = id

        # ------------------------------------------------------------------------------
        # assign stack level tags to stack
        # ------------------------------------------------------------------------------
        for key, value in stack["tags"].items():
            Tags.of(self).add(key, value)
