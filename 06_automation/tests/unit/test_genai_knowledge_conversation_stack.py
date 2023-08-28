import aws_cdk as core
import aws_cdk.assertions as assertions
from infrastructure.genai_knowledge_conversation_stack import (
    GenaiKnowledgeConversationStack,
)


# example tests. To run these tests, uncomment this file along with the example
# resource in infrastructure/genai_knowledge_conversation_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = GenaiKnowledgeConversationStack(app, "genai-knowledge-conversation")
    template = assertions.Template.from_stack(stack)


#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
