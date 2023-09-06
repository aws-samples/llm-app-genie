#!/bin/bash
set -e

wget https://d2eo22ngex1n9g.cloudfront.net/Documentation/SDK/bedrock-python-sdk.zip
unzip -d bedrock-python-sdk bedrock-python-sdk.zip && rm -rf bedrock-python-sdk.zip
