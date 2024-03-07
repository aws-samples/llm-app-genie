import json
from typing import Sequence, Union

from aws_cdk import CustomResource, Duration, RemovalPolicy, Stack, Tags, CfnTag, Names
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr_assets
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_lambda_python_alpha as lambda_python
from aws_cdk import aws_secretsmanager as sm
from aws_cdk import custom_resources as cr
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ssm as ssm
from constructs import Construct
from modules.config import config
from modules.stack import GenAiStack

stack = {
    "description": "Generative AI Chatbot Application",
    "tags": {},
}


class ChatbotVPCStack(GenAiStack):

    vpc: ec2.IVpc
    subnets: Sequence[ec2.ISubnet]


    # def __init__(self, scope: Construct, construct_id: str, config: Config, **kwargs) -> None:
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        cidr_range: str = "10.0.0.0/16",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)


        public_subnet = ec2.SubnetConfiguration(
            name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
        )
        private_subnet = ec2.SubnetConfiguration(
            name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24
        )
        vpc = ec2.Vpc(
            scope=self,
            id="ChatbotVPC",
            ip_addresses=ec2.IpAddresses.cidr(cidr_range),
            max_azs=2,
            nat_gateway_provider=ec2.NatProvider.gateway(),
            nat_gateways=1,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[public_subnet, private_subnet],
            flow_logs={
                "cloudwatch":ec2.FlowLogOptions(
                    destination=ec2.FlowLogDestination.to_cloud_watch_logs()
                # Use default configuration. See also https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/FlowLogOptions.html#aws_cdk.aws_ec2.FlowLogOptions
            )
            }
        )
            

        self.vpc = vpc

        self.subnets = vpc.private_subnets + vpc.isolated_subnets + vpc.public_subnets

        # ==================================================
        # ============= ECR Private Endpoint ===============
        # ==================================================

        _ecr_endpoint_sg = ec2.SecurityGroup(
            self,
            "ECREndpointSecurityGroup",
            vpc=vpc,
            description="Allow access to the ECR Private Endpoint",
            allow_all_outbound=False,
            disable_inline_rules=True,
        )

        ecr_api_vpc_endpoint = vpc.add_interface_endpoint(
            id="AmazonECRAPIVPCEndpoint",
            service=ec2.InterfaceVpcEndpointService(
                f"com.amazonaws.{self.region}.ecr.api", 443
            ),
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(
                one_per_az=True
            ),
            security_groups=[_ecr_endpoint_sg],
        )

        ecr_dkr_vpc_endpoint = vpc.add_interface_endpoint(
            id="AmazonECRDKRVPCEndpoint",
            service=ec2.InterfaceVpcEndpointService(
                f"com.amazonaws.{self.region}.ecr.dkr", 443
            ),
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(
                one_per_az=True
            ),
            security_groups=[_ecr_endpoint_sg],
        )



