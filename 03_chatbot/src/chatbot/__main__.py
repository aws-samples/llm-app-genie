import os

from chatbot.helpers import ChatbotEnvironment
from chatbot.ui import write_chatbot

dirname = os.path.dirname(__file__)

environment = ChatbotEnvironment()
write_chatbot(dirname, environment)
