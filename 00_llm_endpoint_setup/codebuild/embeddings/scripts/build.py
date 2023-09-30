import argparse
import json
import logging
import os

import boto3
from sagemaker.huggingface.model import HuggingFaceModel

logger = logging.getLogger(__name__)
sm_client = boto3.client("sagemaker")


def extend_config(args, stage_config):
    """
    Extend the stage configuration with additional parameters and tags based.
    """
    # Create new params and tags

    model = HuggingFaceModel(
        transformers_version="4.26", pytorch_version="1.13", py_version="py39"
    )

    new_params = {
        "ModelExecutionRoleArn": args.model_execution_role,
        "EndpointInstanceType": args.instance_type,
        "Image": model.serving_image_uri(
            region_name=args.region, instance_type=args.instance_type
        ),
        "Region": args.region,
        "ModelDataUrl": args.s3_model_data_url,
        "EndpointName": args.endpoint_name,
    }

    return {
        "Parameters": {**new_params},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-level", type=str, default=os.environ.get("LOGLEVEL", "INFO").upper()
    )
    parser.add_argument("--model-execution-role", type=str, required=True)
    parser.add_argument("--instance-type", type=str, required=True)
    parser.add_argument("--export-config", type=str, required=True)
    parser.add_argument("--s3-model-data-url", type=str, required=True)
    parser.add_argument("--region", type=str, required=True)
    parser.add_argument("--endpoint-name", type=str, required=True)

    args, _ = parser.parse_known_args()

    # Configure logging to output the line number and message
    log_format = "%(levelname)s: [%(filename)s:%(lineno)s] %(message)s"
    logging.basicConfig(format=log_format, level=args.log_level)

    # Write the staging config
    config = extend_config(args, {})
    logger.debug("config: {}".format(json.dumps(config, indent=4)))
    with open(args.export_config, "w") as f:
        json.dump(config, f, indent=4)
