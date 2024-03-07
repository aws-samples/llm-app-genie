# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin
import json
from typing import Optional

from aws_cdk import CfnOutput, RemovalPolicy
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_opensearchservice as opensearch
from aws_cdk import aws_secretsmanager as sm
from aws_cdk import aws_ssm as ssm
from constructs import Construct
from modules.config import config
from modules.stack import GenAiStack
from stacks.opensearch_domain.opensearch_private_vpc_stack import (
    OpenSearchPrivateVPCStackOutput,
)

stack = {
    "description": "OpenSearch Domain", 
    "tags": {
        "genie:secrets-id": f"{config['appPrefix']}OpenSearchCredentials",
        "genie:index-name": config['opensearch']['index'],
        "genie:sagemaker-embedding-endpoint-name": f"{config['appPrefix']}{config['sagemaker']['embeddings_endpoint_name']}",
        "genie:friendly-name": f"OpenSearch Domain - {config['customer']['name']}"
    }
}


class OpenSearchVpcOutput:
    vpc: ec2.IVpc
    security_group_id: str

    def __init__(self,vpc: ec2.IVpc, security_group_id: str) -> None:
        self.vpc = vpc
        self.security_group_id = security_group_id
        
    


class OpenSearchOutputProps:
    domain: opensearch.Domain
    vpc_endpoint_output: Optional[OpenSearchVpcOutput]


class OpenSearchStack(GenAiStack):
    """
    This class creates a OpenSearch domain with credentials stored in AWS Secrets Manager.
    """

    output_props: OpenSearchOutputProps = OpenSearchOutputProps()

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc_output: Optional[OpenSearchPrivateVPCStackOutput] = None,
        # deploy_in_vpc = False,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        vpc = None
        subnet_selection = None
        domain_kwargs = {
            "capacity": opensearch.CapacityConfig(
                data_nodes=1,
                data_node_instance_type=config["opensearch"]["instance_type"],
                master_nodes=3
            ),
        }
        if vpc_output:
            vpc = vpc_output.vpc
            subnet_selection = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, one_per_az=True )

            open_search_sg = ec2.SecurityGroup(
                self,
                "OpenSearchDomainSecurityGroup",
                vpc=vpc,
                description="Security group for the endpoint inside the OpenSearch domain vpc.",
                allow_all_outbound=True,
                disable_inline_rules=True,
            )

            domain_kwargs = {
                "vpc": vpc,
                "vpc_subnets": [subnet_selection],
                "zone_awareness": opensearch.ZoneAwarenessConfig(
                    availability_zone_count=len(vpc.availability_zones), enabled=True
                ),
                "capacity": opensearch.CapacityConfig(
                    data_node_instance_type=config["opensearch"]["instance_type"],
                    data_nodes=len(vpc.availability_zones),
                    master_nodes=3
                ),
                "security_groups":[open_search_sg]
            }

            self.output_props.vpc_endpoint_output = OpenSearchVpcOutput(vpc=vpc, security_group_id=open_search_sg.security_group_id)
        else:
            print(
f"""
##################################WARNING##################################
    If you are deploying an OpenSearch domain we recommend to deploy
    the {config['appPrefixLowerCase']}PrivateOpenSearchDomainStack stack.
    It deploys the domain into a VPC for improved network security.

    @DEPRECATED: The {config['appPrefixLowerCase']}OpenSearchDomainStack 
                may be removed in a future release.
###########################################################################
"""
            )

        policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            principals=[iam.ArnPrincipal("*")],
            actions=["es:*"],
            resources=[
                f"arn:aws:es:{self.region}:{self.account}:domain/{config['appPrefixLowerCase']}{config['opensearch']['domain'].lower()}*/*"
            ],
        )

        cdk_opensearch_pw = sm.Secret(
            scope=self,
            # do we need id and name
            id="OpenSearchCredentials",
            secret_name=config["appPrefix"] + "OpenSearchCredentials",
            generate_secret_string=sm.SecretStringGenerator(
                secret_string_template=json.dumps({"user": "admin"}),
                generate_string_key="password",
                password_length=20,
            ),
        )

        domain = opensearch.Domain(
            self,            
            config["appPrefix"] + config["opensearch"]["domain"],
            version=opensearch.EngineVersion.OPENSEARCH_2_7,
            ebs=opensearch.EbsOptions(
                volume_size=100, volume_type=ec2.EbsDeviceVolumeType.GP2
            ),
            node_to_node_encryption=True,
            encryption_at_rest=opensearch.EncryptionAtRestOptions(enabled=True),
            removal_policy=RemovalPolicy.RETAIN,
            enforce_https=True,
            access_policies=[policy_statement],
            fine_grained_access_control=opensearch.AdvancedSecurityOptions(
                master_user_name="admin",
                master_user_password=cdk_opensearch_pw.secret_value_from_json(
                    "password"
                ),
            ),
            logging=opensearch.LoggingOptions(
                slow_search_log_enabled=True,
                app_log_enabled=True
            ),
            **domain_kwargs,
        )

        self.output_props.domain = domain

        # ==================================================
        # =================== OUTPUTS ======================
        # ==================================================
        CfnOutput(
            scope=self,
            id=config["appPrefix"] + "OpenSearchDomainEndpoint",
            value=domain.domain_endpoint,
        )

        # Store in SSM
        domain_endpoint_ssm_param = ssm.StringParameter(
            scope=self,
            id="OpenSearchEndpoint",
            parameter_name=config["appPrefix"] + "OpenSearchEndpoint",
            string_value=f"https://{domain.domain_endpoint}:443",
        )

        domain_endpoint_ssm_param.node.add_dependency(domain)

    @property
    def output(self) -> OpenSearchOutputProps:
        return self.output_props
