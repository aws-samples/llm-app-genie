# syntax=docker/dockerfile:1
ARG LISTEN_PORT=80

FROM public.ecr.aws/docker/library/python:3.10-slim as poetry_base


ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.5.1 \
    POETRY_HOME="/opt/poetry"

ENV PATH="$POETRY_HOME/bin:$PATH"

# System deps:
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential \
        wget \
        unzip


# Install Poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | python3 -

RUN apt-get purge --auto-remove -y \
      build-essential

FROM poetry_base
ARG LISTEN_PORT
ENV YOUR_ENV="production"

ENV APP_DIR "/code"

ENV YOUR_ENV=${YOUR_ENV} \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONHASHSEED=random \
  APP_DIR=${APP_DIR} \
  POETRY_VIRTUALENVS_IN_PROJECT=true \
  POETRY_CACHE_DIR=".cache" \
  VIRTUAL_ENVIRONMENT_PATH="${APP_DIR}/.venv" \
  LISTEN_PORT=${LISTEN_PORT} \
  STREAMLIT_CONFIG_DIR=".streamlit"



# Adding the virtual environment to PATH in order to "activate" it.
# https://docs.python.org/3/library/venv.html#how-venvs-work
ENV PATH="$VIRTUAL_ENVIRONMENT_PATH/bin:$PATH"

# Principle of least privilege: create a new user for running the application
RUN groupadd docker
RUN useradd -r -g docker python_application

# Copy only requirements to cache them in docker layer
WORKDIR $APP_DIR

RUN chown python_application:docker $APP_DIR

# Create cache directory and set permissions because user has no home
# and poetry cache directory.
# https://python-poetry.org/docs/configuration/#cache-directory
RUN mkdir ${POETRY_CACHE_DIR} && chown python_application:docker ${POETRY_CACHE_DIR}

# Allow execution and read by user and group
COPY --chown=python_application:docker --chmod=550 entrypoint.sh ./
COPY --chown=python_application:docker --chmod=550 download_bedrock_sdk.sh ./
COPY --chown=python_application:docker --chmod=550 generate_secrets.py ./

COPY --chown=python_application:docker poetry.lock pyproject.toml ./
# Download the bedrock-python-sdk
RUN ./download_bedrock_sdk.sh
RUN chown python_application:docker ./bedrock-python-sdk/

# activate after adding bedrock sdk
RUN mkdir ${STREAMLIT_CONFIG_DIR} && chown python_application:docker ${STREAMLIT_CONFIG_DIR}

# Project initialization:
RUN poetry install --no-interaction --no-ansi --no-root

# copy source code files
COPY --chown=python_application:docker src ./src/

HEALTHCHECK CMD curl --fail http://localhost:${LISTEN_PORT}/_stcore/health

USER python_application
EXPOSE ${LISTEN_PORT}

ENTRYPOINT ["./entrypoint.sh"]

