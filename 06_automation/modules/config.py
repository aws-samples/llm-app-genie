import json
import os

import boto3

# ------------------------------------------------------------------------------
# import environment configuration based on the STAGE
# ------------------------------------------------------------------------------
# Load the Environment Configuration from the JSON file
with open(
    "configs/" + (os.environ["STAGE"] if "STAGE" in os.environ else "dev") + ".json",
    "r", 
    encoding="utf8"
) as file:
    config = json.load(file)

# Adding environment and prefix
config["appPrefix"] = os.environ["CDK_APP_PREFIX"] if "CDK_APP_PREFIX" in os.environ else "Genie"
config["appPrefixLowerCase"] = config["appPrefix"].lower()


# adding CODEBUILD_BUILD_NUMBER to the version tag
config["globalTags"]["version"] += "." + (
    os.environ["CODEBUILD_BUILD_NUMBER"]
    if "CODEBUILD_BUILD_NUMBER" in os.environ
    else ""
)

# add application prefix to all tags
global_tags = {}
for key, value in config["globalTags"].items():
    key = config["appPrefixLowerCase"] + ":" + key
    global_tags[key] = value

config["globalTags"] = global_tags

quotas_client = boto3.client(
    "service-quotas", region_name=os.environ["CDK_DEFAULT_REGION"]
)
quotas = {
    "ml.g5.12xlarge": "L-65C4BD00",
    "ml.g5.48xlarge": "L-0100B823",
    "ml.g4dn.xlarge": "L-B67CFA0C",
}
