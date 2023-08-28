import aws_cdk as cdk
from constructs import Construct

from .chatbot_stack import ChatbotStack


class ChatbotAppStage(cdk.Stage):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ChatbotStack(self, "ChatbotStack", **kwargs)
