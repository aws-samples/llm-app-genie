# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin
import json

from aws_cdk import CfnOutput, RemovalPolicy, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_opensearchservice as opensearch
from aws_cdk import aws_secretsmanager as sm
from aws_cdk import aws_ssm as ssm
from constructs import Construct
from modules.config import config
from modules.stack import GenAiStack

stack = {"description": "OpenSearch Domain", "tags": {}}


class OpenSearchStack(GenAiStack):
    """
    This class creates a OpenSearch domain with credentials stored in AWS Secrets Manager.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            principals=[iam.ArnPrincipal("*")],
            actions=["es:*"],
            resources=[
                f"arn:aws:es:{self.region}:{self.account}:domain/{config['appPrefixLC']}-{config['opensearch']['domain']}/*"
            ],
        )

        cdk_opensearch_pw = sm.Secret(
            scope=self,
            id=config["appPrefixLC"] + "opensearch_pw",
            secret_name=config["appPrefixLC"] + "_opensearch_pw",
            generate_secret_string=sm.SecretStringGenerator(
                secret_string_template=json.dumps({"user": "admin"}),
                generate_string_key="password",
                password_length=20,
            ),
        )

        ## TODO: create the domain in a private subnet
        domain = opensearch.Domain(
            self,
            config["appPrefixLC"] + "Domain",
            domain_name=config["appPrefixLC"] + "-" + config["opensearch"]["domain"],
            version=opensearch.EngineVersion.OPENSEARCH_2_7,
            ebs=opensearch.EbsOptions(
                volume_size=100, volume_type=ec2.EbsDeviceVolumeType.GP2
            ),
            capacity=opensearch.CapacityConfig(
                data_nodes=1, data_node_instance_type="t3.medium.search"
            ),
            node_to_node_encryption=True,
            encryption_at_rest=opensearch.EncryptionAtRestOptions(enabled=True),
            removal_policy=RemovalPolicy.DESTROY,  # or RETAIN?
            enforce_https=True,
            access_policies=[policy_statement],
            fine_grained_access_control=opensearch.AdvancedSecurityOptions(
                master_user_name="admin",
                master_user_password=cdk_opensearch_pw.secret_value_from_json(
                    "password"
                ),
            ),
        )

        # Needed by the app to fetch configs from AWS tagged resources
        Tags.of(domain).add(f"{config['appPrefixLC']}:secrets-id", f"{config['appPrefixLC']}_opensearch_pw")
        Tags.of(domain).add(
            f"{config['appPrefixLC']}:index-name", config["opensearch"]["index"]
        )
        Tags.of(domain).add(
            f"{config['appPrefixLC']}:sagemaker-embedding-endpoint-name",
            config["sagemaker"]["embeddings_endpoint_name"],
        )
        Tags.of(domain).add(
            f"{config['appPrefixLC']}:friendly-name",
            f"OpenSearch Index: {config['customer']['name']}",
        )
        # ==================================================
        # =================== OUTPUTS ======================
        # ==================================================
        CfnOutput(
            scope=self,
            id=config["appPrefix"] + "OpenSearchDomainEndpoint",
            value=domain.domain_endpoint,
        )

        # Store in SSM
        ssm.StringParameter(
            scope=self,
            id=config["appPrefix"] + "OpenSearchEndpointParamter",
            parameter_name=config["appPrefixLC"] + "_opensearch_endpoint",
            string_value=f"https://{domain.domain_endpoint}:443",
        )
