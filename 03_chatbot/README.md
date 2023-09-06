# Chatbot App

This applications contains the frontend and chatbot logic for some common generative AI patterns, such as Retrieval Augmented Generation (RAG) of answers.
It allows selecting from the large language models (LLMs) and knowledge bases (KBs) available in the account where the solution is deployed. You can read more about the LLMs and KBs that the application uses in the [Discovery of available Knowledge bases and LLMs section](#discovery-of-available-knowledge-bases-and-llms)

The usable LLMs are accessible either via Amazon Bedrock or Amazon SageMaker endpoints.
The usable KBs are accessible either via Amazon Kendra indices or Amaozn OpenSearch Service clusters.

You can run locally the ChatBot Streamlit app in two ways:

1. [build and run the streamlit container via Docker](#running-the-streamlit-chatbot-app-using-docker), or
2. [running the streamlit app locally](#running-the-chatbot-app-using-streamlit)

The application uses the AWS Region configured through the `AWS_DEFAULT_REGION` environment variable. For Amazon Bedrock, it uses the AWS Region defined in the `BEDROCK_REGION` environment variable.

To set these environment variables in Linux/MacOS run the following commands in the terminal where you plan to execute the application from or define them in the container.

```bash
export AWS_DEFAULT_REGION=eu-west-1
export BEDROCK_REGION=us-west-2
```

## Environment Variables

The chatbot allows you to configure the following environment variables.

| Variable Name              | Default Value | Usage                                                                                                                                                                                                                                                             |
| -------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AWS_DEFAULT_REGION         | eu-west-1     | The AWS region that the chatbot is running in and that contains Amazon OpenSearch domains, Kendra indices, and language models.                                                                                                                                   |
| BEDROCK_REGION             | None          | The chatbot uses Amazon Bedrock in this region. See also [Amazon Bedrock](#amazon-bedrock)                                                                                                                                                                        |
| BASE_URL                   | no default    | Base URL from which the chatbot web app is served. Not used.                                                                                                                                                                                                      |
| AWS_APP_CONFIG_APPLICATION | no default    | Optional AWS AppConfig application name if the chatbot should use AWS AppConfig for configuration instead of json file. Needs to be set together with AWS_APP_CONFIG_ENVIRONMENT and AWS_APP_CONFIG_PROFILE. See also [Personalize the app](#personalize-the-app) |
| AWS_APP_CONFIG_ENVIRONMENT | no default    | Optional AWS AppConfig environment name if the chatbot should use AWS AppConfig for configuration instead of json file. Needs to be set together with AWS_APP_CONFIG_APPLICATION and AWS_APP_CONFIG_PROFILE. See also [Personalize the app](#personalize-the-app) |
| AWS_APP_CONFIG_PROFILE     | no default    | Optional AWS AppConfig profile name if the chatbot should use AWS AppConfig for configuration instead of json file. Needs to be set together with AWS_APP_CONFIG_APPLICATION and AWS_APP_CONFIG_ENVIRONMENT. See also [Personalize the app](#personalize-the-app) |

In code all environment variables are defined in [ChatbotEnvironmentVariables](./src/chatbot/config/environment_variables.py).

## Running the streamlit chatbot app using Docker

Dependencies:

- Docker cli installed locally

Lets navigate to the chatbot folder:

```bash
cd <cloned-repository>/03_chatbot
```

Now we first build the container:

```bash
docker build  . -t streamlit-src
```

In order to communicate with Amazon Kendra/Amazon OpenSearch Service and Amazon SageMaker, you need to have permissions to invoke the service.
In order to pass AWS credentials you can pass the credentials at run time via ENV variables.

Create a file `env.list` which contains the credentials grand the chatbot access to AWS services, and the credentials needed by the user to access the chatbot UI (`USERNAME` and `PASSWORD`)

```bash
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
AWS_DEFAULT_REGION=...
USERNAME=...
PASSWORD=...
```

Run the container with the `env.list` file:

```bash
docker run -p 127.0.0.1:80:80 --env-file env.list streamlit-src
```

You can now access the streamlit application from your browser at [localhost](http://localhost).

## Running the chatbot app using streamlit

Dependencies:

- Python 3.10
- poetry

Installing poetry

```bash
brew install poetry
```

or

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Your local Streamlit app will read secrets from a file `.streamlit/secrets.toml` in your app's root dir.
Create this file if it doesn't exist yet and add the usernames & password to it as shown below:

```toml
# .streamlit/secrets.toml

[passwords]
# Follow the rule: username = "password"
Ana = "passwordEXAMPLE"
"John Doe" = "password2EXAMPLE"
```

More information about Streamlit authentication can be found [here](https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso)

Make sure that you have defined the [environment variables that the chatbot uses](#environment-variables).

Go to the `03_chatbot` directory

```bash
cd <cloned-repository>/03_chatbot
poetry install
poetry shell
streamlit run src/run_module.py --server.enableCORS true --server.port 80 --browser.serverPort 80
```

## Discovery of available Knowledge bases and LLMs

The application uses [tags](https://docs.aws.amazon.com/tag-editor/latest/userguide/tagging.html) to discover the available AWS resources for information retrieval and LLMs you are running.

The application looks for resources with tag key `gena:friendly-name` in the `AWS_DEFAULT_REGION` you configured. You should set the value of the `gena:friendly-name` tag to a human-readable string that the app shows to the users. The gena friendly name needs to be unique.
Note that if you deploy resources using the provided CDK stacks as described in [Deploy the foundational infrastructure](../README.md#deploy-the-foundational-infrastructure).

| Tag Key            | Tag Value                                                                                                                                                                                                                                                                                                                                                                                        | Example Value                           |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| gena:friendly-name | Pick a human-readable name that you want the index or LLM to show up in the front-end                                                                                                                                                                                                                                                                                                            | Falcon 40B Instruct                     |
| gena:prompt-rag    | Amazon S3 URI, local path, or [LangChainHub](https://github.com/hwchase17/langchain-hub) path that contains prompt template to use when asking questions based on documents to this model. See also [LangChain Serialization](https://python.langchain.com/docs/modules/model_io/prompts/prompt_templates/prompt_serialization) documentation to learn what format a prompt template file needs. | prompts/falcon_chat.yaml                |
| gena:prompt-chat   | Amazon S3 URI, local path, or [LangChainHub](https://github.com/hwchase17/langchain-hub) path that contains prompt template to use when chatting with this model. See also [LangChain Serialization](https://python.langchain.com/docs/modules/model_io/prompts/prompt_templates/prompt_serialization) documentation to learn what format a prompt template file needs.                          | s3://DOC-EXAMPLE-BUCKET/prompt_key.json |

Here is an example of how to tag an Amazon SageMaker inference endpoint to enable the use of that LLM in the app.
![Amaxon SageMaker inference endpoint Add/Edit tags screenshot showing tag with gena:friendly-name as key and Falcon 40B Instruct as value.](/images/Amazon%20SageMaker%20endpoint%20tags%20dynamic%20discovery.png "Amazon SageMaker inference endpoint gena:friendly-name tag.")

### Amazon OpenSearch domain tags

For the app to dynamically discovery your Amazon OpenSearch index you need to add the following tags to your Amazon OpenSearch domain.

| Tag Key                                | Tag Value                                                                                                                                                              | Example Value                     |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| gena:friendly-name                     | Pick a human readable name that you want the index to show up in the front-end as                                                                                      | My OpenSearch movie reviews index |
| gena:index-name                        | The name of your OpenSearch index which contains your documents                                                                                                        | movies                            |
| gena:sagemaker-embedding-endpoint-name | The name of your Amazon SageMaker inference endpoint that is running the embedding model that you used to create embeddings for the documents in your OpenSearch index | embeddings-e5-large-v2            |
| gena:secrets-id                        | The name of your secret in AWS Secrets Manager that stores the username and password to connect to your OpenSearch index                                               | opensearch_pw                     |

### Amazon DynamoDB table for memory tags

The app needs an Amazon DynamoDB table to keep the chat history across sessions. The app finds the Amazon DynamoDB tables with `gena:memory-table` as a resource tag. The app uses the first table with that tag that it discovers.

When creating the Amazon DynamoDB table use `SessionId` with type `String` as the partition key.

| Tag Key           | Tag Value | Example (Key, Value)               |
| ----------------- | --------- | ---------------------------------- |
| gena:memory-table | Not used  | (gena:memory-table, "MemoryTable") |

## Amazon Bedrock

To use Amazon Bedrock, you need the Amazon Bedrock SDK.
If you want to run the chatbot locally, you need to download the Amazon Bedrock SDK locally into the [`03_chatbot/bedrock-python-sdk`](../03_chatbot/bedrock-python-sdk/) directory.
We provide a [script (download_bedrock_sdk)](./download_bedrock_sdk.sh) to download and unzip the Amazon Bedrock SDK.

```Bash
cd 03_chatbot/
./download_bedrock_sdk.sh
```

If you deploy the chatbot to AWS using `cdk`, you dont need to do anything as it gets automatically installed in the Docker image.

The easy configuration for the app to use Amazon Bedrock is to set the `BEDROCK_REGION` environment variable (see also [Environment Variables](#environment-variables)). The app will discover the Amazon Bedrock models in that region.

If you want the app to use Amazon Bedrock in multiple regions or you want to control more of the app configuration for Amazon Bedrock then you should take a look at the [Personalize the app](#personalize-the-app) section. If you configure an AWS Region for Amazon Bedrock usage through the app configuration and the environment variable then the app configuration takes precedent.

## Personalize the app

You can change the name and the icon of the app by adjusting `appconfig.json`.
For the extensive configuration specification take a look at the [App Config JSON Schema](/src/chatbot/json_schema/aws_awsomechat_app_config.schema.json).

Optionally you can also configure more details on how the app uses Amazon Bedrock.

Here is an example `appconfig.json`:

```json
{
  "$schema": "./json_schema/aws_awsomechat_app_config.schema.json",
  "appearance": {
    "type": "AWSomeChatAppearance",
    "parameters": {
      "name": "My Chatbot",
      "faviconUrl": "https://a0.awsstatic.com/libra-css/images/logos/aws_smile-header-desktop-en-white_59x35@2x.png"
    }
  }
}
```

### Optional Amazon Bedrock config

To get started with Amazon Bedrock follow the [Amazon Bedrock](#amazon-bedrock) section.

If you want to configure Amazon Bedrock in multiple regions, use a different endpoint, or want to configure the chatbot IAM access to Amazon Bedrock then you can use `appconfig.json`.

Here is an example `appconfig.json` with Amazon Bedrock in multiple regions:

```json
{
  "$schema": "./json_schema/aws_awsomechat_app_config.schema.json",
  "appearance": {
    "type": "AWSomeChatAppearance",
    "parameters": {
      "name": "My Chatbot",
      "faviconUrl": "https://a0.awsstatic.com/libra-css/images/logos/aws_smile-header-desktop-en-white_59x35@2x.png"
    }
  },
  "amazonBedrock": [
    {
      "type": "AmazonBedrock",
      "parameters": {
        "region": "us-east-1"
      }
    },
    {
      "type": "AmazonBedrock",
      "parameters": {
        "region": "us-west-2"
      }
    }
  ]
}
```

Here is an example `appconfig.json` specifing the Amazon Bedrock endpoint:

```json
{
  "$schema": "./json_schema/aws_awsomechat_app_config.schema.json",
  "appearance": {
    "type": "AWSomeChatAppearance",
    "parameters": {
      "name": "My Chatbot",
      "faviconUrl": "https://a0.awsstatic.com/libra-css/images/logos/aws_smile-header-desktop-en-white_59x35@2x.png"
    }
  },
  "amazonBedrock": [
    {
      "type": "AmazonBedrock",
      "parameters": {
        "region": "us-east-1",
        "endpointURL": "https://bedrock.us-east-1.amazonaws.com"
      }
    }
  ]
}
```

Here is an example `appconfig.json` specifying the [profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) or a second one specifying the IAM role to use for Amazon Bedrock access:

```json
{
  "$schema": "./json_schema/aws_awsomechat_app_config.schema.json",
  "appearance": {
    "type": "AWSomeChatAppearance",
    "parameters": {
      "name": "My Chatbot",
      "faviconUrl": "https://a0.awsstatic.com/libra-css/images/logos/aws_smile-header-desktop-en-white_59x35@2x.png"
    }
  },
  "amazonBedrock": [
    {
      "type": "AmazonBedrock",
      "parameters": {
        "region": "us-east-1",
        "iam": {
          "type": "BotoIAM",
          "parameters": {
            "profile": "<YOUR_PROFILE_NAME>"
          }
        }
      }
    },
    {
      "type": "AmazonBedrock",
      "parameters": {
        "region": "us-east-1",
        "endpointURL": "https://bedrock.us-east-1.amazonaws.com",
        "iam": {
          "type": "BotoIAM",
          "parameters": {
            "profile": "arn:aws:iam::<YOUR_ACCOUNT_ID>:role/<YOUR_ROLE_NAME>"
          }
        }
      }
    }
  ]
}
```

If you are a developer and want to add more configuration options to this application then you should read the [Readme in the json_schema directory](src/chatbot/json_schema/Readme).

or setting the following env variables to load the configuration from AWS App Config.

If you want to use AWS AppConfig create a configuration in AWS AppConfig: [AWS AppConfig User Guide](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-application.html).
In AWS AppConfig use the same JSON structure as described above for `appconfig.json`.
Replace the values of the below environment variables with the names you used when creating your AWS AppConfig configuration.

```bash
export AWS_APP_CONFIG_APPLICATION=ChatbotApp
export AWS_APP_CONFIG_ENVIRONMENT="ChatbotApp Environment"
export AWS_APP_CONFIG_PROFILE=Chatbot
```

## Internationalization (i18n)

We use [Babel](https://babel.pocoo.org/en/latest/index.html) as the translation workflow tool.
During runtime we use [gettext](https://docs.python.org/3/library/gettext.html#class-based-api) for internationalization.

If you are adding UI text to the app you should wrap it in `_(...)` so that the string can be internationalized. Here is an example how your UI text code should look like.

```python
import gettext

_ = gettext.gettext
my_ui_text = _("Hello World in your language!")

my_ui_text_with_format = _("Your language is: {language}").format(language="German")
#Notice that .format is called outside of _(...)

# use my_ui_text and my_ui_text_with_format like any other string
```

### Translation Pipeline

Make sure that you have the Poetry dev dependencies installed.
Run the following bash commands from the `03_chatbot` directory.

#### Add a new language

To add a new langauge run and replace `-l de_DE` with the local code of the new language.

```bash
pybabel init -i "./src/chatbot/i18n/chatbot.pot" \
--domain=chatbot \
-d "./src/chatbot/i18n" \
-l de_DE
```

Next step: [Translate](#translate)

#### Extract text that needs internationalization

If you add, modify, or delete UI text that needs internationalization marked with `_(...)` run the following bash command to extract all the string marked for internationalization in the code.

Add yourself as an author in the `--header-comment`.

```bash
pybabel extract ./src -o "./src/chatbot/i18n/chatbot.pot" \
--msgid-bugs-address=malterei@amazon.com \
--version=0.0.1 \
--project=gena \
--header-comment=$'# Translations template for gena. \
\n# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. \
\n# This file is distributed under the same license as the gena project. \
\n# Malte Reimann malterei@amazon.com, 2023.\n'
```

This generates a [chatbot.pot](./src/chatbot/i18n/chatbot.pot) that contains the strings in the application that need internationalization.

Next step: [Update an existing language after code changes](#update-an-existing-language-after-code-changes)

#### Update an existing language after code changes

Replace `-l de_DE` with the language that you are translating. Run the following command which updates any changes in the UI text that need internationalization for that language.

```bash
pybabel update  --previous  --update-header-comment --domain=chatbot \
-i "./src/chatbot/i18n/chatbot.pot" \
-d "./src/chatbot/i18n" \
-l de_DE
```

Next step: [Translate](#translate)

#### Translate

Open the `chatbot.po` file for the language that you are translating with the text editor of your choice. The `chatbot.po` file for a given language is in the `src/chatbot/i18n/<LOCAL_CODE>/LC_MESSAGES` directory.

For example if you are translating to German open [src/chatbot/i18n/de_DE/LC_MESSAGES/chatbot.po](./src/chatbot/i18n/de_DE/LC_MESSAGES/chatbot.po).

The `chatbot.po` file for your language contains the UI text that the application uses and the translation of the text into your language.
The `msgid` is the UI text. Do not change this line.
The `msgstr` is the UI text translated into your language. This is what you can change in the `chatbot.po` file for the language that you are translating.

The following example shows an entry in the `chatbot.po` file for `de_DE` (German) with a UI text that is not yet translated.

```txt
#: src/chatbot/ui/chat_messages.py:59
msgid "You are chatting with {model_name}."
msgstr ""
```

Here is the same entry if the text has already been translated.

```txt
#: src/chatbot/ui/chat_messages.py:59
msgid "You are chatting with {model_name}."
msgstr "Sie chatten mit {model_name}."
```

Translate each `msgid` and write the translated text into `msgstr`. Text in curly brackets (`{}`), for example `{model_name}` are variables. Do not change anything in curly brackets. You can move the position of the curly brackets in the `msgstr`.

An entry that has been changed might still be present in the `chatbot.po` file. They are commented out. You can consider removing them. Here is an example of a previous UI text that has been changed or replaced:

```txt
#~ msgid "{chatbot_name} - An LLM-powered src for your custom data"
#~ msgstr ""
```

Next step: [Compile](#compile)

#### Compile

After modifying or adding new translations they need to be compiled so that the application can use them.

Run the following command to compile internationalixation in all languages.

```bash
pybabel compile -d "./src/chatbot/i18n" --domain=chatbot
```

If you get a massage saying `catalog ./src/chatbot/i18n/de_DE/LC_MESSAGES/chatbot.po is marked as fuzzy, skipping` that means that there is an UI text in the `chatbot.po` file that only changed slighty. It is marked with `#, fuzzy`. A human should review if the translation need updating and then remove the flag in the `chatbot.po` file.

Congrats, now the translation changes are available inside the application. 🎉

## Configure VS Code to run streamlit

Create a launch.json file in `03_chatbot/.vscode/launch.json`.

Write the following launch configuration into your `launch.json` file and replace `<YOUR_AWS_PROFILE_NAME>` with the name of the AWS profile you want to use. To create an AWS profile in VS Code follow the [AWS Toolkit for VS Code - AWS IAM credentials](https://docs.aws.amazon.com/toolkit-for-vscode/latest/userguide/setup-credentials.html#add-credential-profiles) documentation.

```json
{
  // Use IntelliSense to learn about possible attributes.
  // Hover to view descriptions of existing attributes.
  // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Module",
      "type": "python",
      "request": "launch",
      "module": "streamlit",
      "justMyCode": true,
      "args": ["run", "src/run_module.py"],
      "env": { "AWS_PROFILE": "<YOUR_AWS_PROFILE_NAME>" }
    }
  ]
}
```

Use `F5` to debug the streamlit application on VS Code.
