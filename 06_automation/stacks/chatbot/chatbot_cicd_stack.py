from aws_cdk import pipelines
from constructs import Construct
from modules.stack import GenAiStack

from .chatbot_cicd_stages import ChatbotAppStage

stack = {
    "description": "CI/CD pipeline to continuously deploy chatbot and chatbot app infrastructure.",
    "tags": {},
}


class ChatbotCiCdStack(GenAiStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        chatbot_app_stack_source: pipelines.FileSetLocation,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        # pipeline_role = iam.Role(self, "ChatbotPipelineRole",
        #     assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
        #     inline_policies={
        #
        #     }
        # )

        # The code that defines your stack goes here
        pipeline = pipelines.CodePipeline(
            self,
            "Pipeline",
            pipeline_name="ChatbotPipeline",
            #  role=pipeline_role,
            synth=pipelines.ShellStep(
                "Synth",
                input=chatbot_app_stack_source,
                commands=[
                    "npm install -g aws-cdk",
                    "curl -sSL https://install.python-poetry.org | python3 -",
                    'export PATH="/root/.local/bin:$PATH"',
                    "cd 06_automation",
                    "poetry install",
                    'poetry run cdk synth --app "poetry run python app.py"',
                ],
            ),
        )
        pipeline.add_stage(ChatbotAppStage(self, "prod", **kwargs))
