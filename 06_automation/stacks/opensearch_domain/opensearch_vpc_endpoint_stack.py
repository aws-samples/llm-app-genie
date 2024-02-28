from typing import Sequence

from aws_cdk import Names, Tags, Tag, Duration, CustomResource
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from aws_cdk import custom_resources as custom
from aws_cdk import aws_opensearchservice as opensearch
from aws_cdk import aws_lambda_python_alpha as lambda_python
from aws_cdk import aws_lambda as lambda_
from constructs import Construct
from modules.stack import GenAiStack
from modules.config import config


stack = {
    "description": "OpenSearch VPC endpoint in target VPC",
    "tags": {},
}


class OpenSearchVPCEndpointStack(GenAiStack):
    # def __init__(self, scope: Construct, construct_id: str, config: Config, **kwargs) -> None:
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        opensearch_domain: opensearch.IDomain,
        consumer_target_vpc: ec2.IVpc,
        consumer_security_group: ec2.ISecurityGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        opensearch_domain_arn = opensearch_domain.domain_arn

        enbdpoint_sg = ec2.SecurityGroup(
            self,
            "OpenSearchVPCEndpointSecurityGroup",
            vpc=consumer_target_vpc,
            description="Allow access to OpenSearch VPC endpoint",
            allow_all_outbound=False,
            disable_inline_rules=True,
        )
        # This will add the rule as an external cloud formation construct
        enbdpoint_sg.add_ingress_rule(
            consumer_security_group,
            ec2.Port.tcp(443),
            f"allow https access from VPC endpoint consumer security group",
        )

        consumer_subnets = consumer_target_vpc.select_subnets(
            one_per_az=True
        )

        

        vpc_endpoint_function = lambda_python.PythonFunction(
            self,
            "CreateOpenSearchVPCEndpointAndTag",
            entry="./stacks/opensearch_domain/vpc_endpoint_lambda",
            index="function.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.minutes(15),
        )

        provider = custom.Provider(
            self, "OpenSearchVPCEndpointCustomResourceProvider", on_event_handler=vpc_endpoint_function
        )


        vpc_endpoint_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["ec2:CreateTags", "es:CreateVpcEndpoint","ec2:CreateVpcEndpoint", "ec2:DescribeSubnets", "ec2:DescribeSecurityGroups", "ec2:DescribeVpcEndpoints","es:DescribeVpcEndpoints", "es:DeleteVpcEndpoint", "ec2:DeleteVpcEndpoints", "es:AddTags", "es:UpdateVpcEndpoint", "es:RemoveTags"],
                resources=["*"],
            )
        )


        

        vpc_endpoint = CustomResource(
            self,
            "OpenSearchVPCEndpointCustomResource",
            service_token=provider.service_token,
            properties={
                "domain_arn": opensearch_domain_arn,
                "app_prefix": config["appPrefixLowerCase"],
                "subnet_ids": [subnet.subnet_id for subnet in consumer_subnets.subnets],
                "security_group_ids": [enbdpoint_sg.security_group_id]
            },
        )

    

       
        # vpc_endpoint_create_param = {
        #     "DomainArn": opensearch_domain_arn,  # required
        #     "VpcOptions": {  # required
        #         "SecurityGroupIds": [enbdpoint_sg.security_group_id],
        #         "SubnetIds": [subnet.subnet_id for subnet in consumer_subnets.subnets],
        #     },
        #     "ClientToken": construct_id,  # for idempotency
        # }

        # vpc_endpoint_cr = custom.AwsCustomResource(
        #     self,
        #     "CreateOpenSearchVPCEndpointCustomResource",
        #     on_create=custom.AwsSdkCall(
        #         service="@aws-sdk/client-opensearch",
        #         action="CreateVpcEndpoint",
        #         parameters=vpc_endpoint_create_param,
        #         physical_resource_id=custom.PhysicalResourceId.from_response(
        #             "VpcEndpoint.VpcEndpointId"
        #         )
        #     ),
        #     on_update=custom.AwsSdkCall(
        #         service="@aws-sdk/client-opensearch",
        #         action="UpdateVpcEndpoint",
        #         physical_resource_id=custom.PhysicalResourceId.from_response(
        #             "VpcEndpoint.VpcEndpointId"
        #         ),
        #         parameters={
        #             "VpcEndpointId": custom.PhysicalResourceIdReference(),
        #             "VpcOptions": {  # required
        #                 "SecurityGroupIds": [enbdpoint_sg.security_group_id],
        #                 "SubnetIds": [subnet.subnet_id for subnet in consumer_subnets.subnets],
        #             }
        #         }
        #     ),
        #     on_delete=custom.AwsSdkCall(
        #         service="@aws-sdk/client-opensearch",
        #         action="DeleteVpcEndpoint",
        #         parameters={
        #             "VpcEndpointId": custom.PhysicalResourceIdReference()
        #         }
        #     ),
        #     policy=custom.AwsCustomResourcePolicy.from_statements(
        #         statements=[
        #             iam.PolicyStatement(
        #                 resources=["*"], actions=["es:CreateVpcEndpoint","ec2:CreateVpcEndpoint", "ec2:DescribeSubnets", "ec2:DescribeSecurityGroups", "ec2:DescribeVpcEndpoints", "ec2:CreateTags"]
        #             ),
        #             iam.PolicyStatement(
        #                 resources=["*"],
        #                 actions=["es:DeleteVpcEndpoint"]
        #                 ,conditions=
        #                     {
        #                     "StringEquals": {f"aws:ResourceTag/{certificate_conditional_tag['Key']}": certificate_conditional_tag['Value']}
        #                 }
        #             ),
                    
        #         ]
        #     ),
        #     install_latest_aws_sdk=True,
        # )

        # vpc_endpoint = vpc_endpoint_cr.get_response_field("VpcEndpoint.Endpoint")
        # print("VPC endpoint")
        # print(vpc_endpoint)

        # Tag(f"{config['appPrefix']}:CHATBOT_VPC_ENDPOINT", vpc_endpoint).visit(opensearch_domain)
