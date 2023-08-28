#!/bin/bash
set -e
exec poetry run python generate_secrets.py &
exec poetry run streamlit run src/run_module.py --server.enableCORS true --server.port $LISTEN_PORT --browser.serverPort $LISTEN_PORT --browser.gatherUsageStats false