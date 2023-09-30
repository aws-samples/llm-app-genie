#!/bin/bash
set -e
exec poetry run pybabel compile -d "./src/chatbot/i18n" --domain=chatbot
