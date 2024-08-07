# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin
from typing import Sequence, Union

from constructs import Construct
from modules.config import config
from modules.stack import GenAiStack
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ec2 as ec2
from aws_cdk import CfnOutput, RemovalPolicy, Tags
from aws_cdk import aws_iam as iam
from aws_cdk import aws_dynamodb as dynamodb

stack = {
    "description": "Core stack for the chatbot.", 
    "tags": {}
}


class CoreStack(GenAiStack):
    """
    This class creates a Core CDK stack where central core elements for other stack are created
    In object is required for more than 1 stack or may be required later, it should be created here
    """
    vpc: ec2.IVpc
    subnets: Sequence[ec2.ISubnet]
    chatbot_security_group: ec2.ISecurityGroup

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)


        self.chatbot_security_group_id_cfn_output_name = f"{config['appPrefix']}ChatbotSecurityGroupIdOutput"

        self.memory_table = dynamodb.Table(
            self,
            "MemoryTable",
            partition_key=dynamodb.Attribute(
                name="SessionId", type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True
        )

        self.textract_bucket = s3.Bucket(
            self,
            f"TextractBucket",
            versioned=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        self.data_sources_bucket = s3.Bucket(
            self,
            f"DataSources",
            versioned=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        Tags.of(self.memory_table).add(
            f"genie:memory-table",
            "Use this table to store the history",
        )

        # ==================================================
        # ========== Global VPC for the Chatbot ============
        # ==================================================
        public_subnet = ec2.SubnetConfiguration(
            name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=config["vpc"]["cidr_mask"]
        )
        private_subnet = ec2.SubnetConfiguration(
            name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=config["vpc"]["cidr_mask"]
        )
        vpc = ec2.Vpc(
            scope=self,
            id="ChatbotVPC",
            ip_addresses=ec2.IpAddresses.cidr(config["vpc"]["cidr_range"]),
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

        chatbot_sg = ec2.SecurityGroup(
            self,
            "ChatbotSecurityGroup",
            vpc=vpc,
            description="Chatbot service security group",
            allow_all_outbound=True,
            disable_inline_rules=True,
        )

        # Export chatbot security group id to prevent cyclic references.
        CfnOutput(self,
            self.chatbot_security_group_id_cfn_output_name,
            value=chatbot_sg.security_group_id,
            export_name=self.chatbot_security_group_id_cfn_output_name,
            description="Chatbot security group id."
        )


        self.chatbot_security_group = chatbot_sg    
        self.vpc = vpc
        self.subnets = vpc.private_subnets + vpc.isolated_subnets + vpc.public_subnets

        


        # ==================================================
        # ========== IAM self.ROLE for the ECS task ========
        # ==================================================
        self.role = iam.Role(
            scope=self,
            id="Taskself.role",
            assumed_by=iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
        )
        self.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonECS_FullAccess")
        )
        self.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonEC2ContainerRegistryReadOnly"
            )
        )


        endpoint_sg = ec2.SecurityGroup(
            self,
            f"ChatbotVPCEndpointsSecurityGroup",
            vpc=vpc,
            description=f"Allow access from the Chatbot to the Private Endpoint",
            allow_all_outbound=True,
            disable_inline_rules=True,
        )

        endpoint_sg.add_ingress_rule(
            chatbot_sg,
            connection=ec2.Port.tcp(443),
            description=f"Allow inbound from chatbot for {config['appPrefixLowerCase']}-ai-app",
        )

        # ==================================================
        # ============= ECR Private Endpoints ===============
        # ==================================================
        self.create_interface_endpoint_for_chatbot(endpoint_sg, "ecr.api", vpc)
        self.create_interface_endpoint_for_chatbot(endpoint_sg, "ecr.dkr", vpc)


        # ==================================================
        # ============== AWS Secrets Manager ===============
        # ==================================================
        self.create_interface_endpoint_for_chatbot(endpoint_sg, "secretsmanager", vpc)


        # ==================================================
        # ================= Logs Endpoints =================
        # ==================================================
        self.create_interface_endpoint_for_chatbot(endpoint_sg, "logs", vpc)
        self.create_interface_endpoint_for_chatbot(endpoint_sg, "ecs-agent", vpc)
        self.create_interface_endpoint_for_chatbot(endpoint_sg, "ecs-telemetry", vpc)


        # ==================================================
        # ================== S3 Endpoint ===================
        # ==================================================
        vpc.add_gateway_endpoint("S3GatewayEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3
        )
        
      
    def create_interface_endpoint_for_chatbot(self, endpoint_sg, endpoint_name, vpc):
        

        vpc.add_interface_endpoint(
            id=f"{endpoint_name}ManagerVPCEndpoint",
            service=ec2.InterfaceVpcEndpointService(
                f"com.amazonaws.{self.region}.{endpoint_name}", 443
            ),
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(
                one_per_az=True
            ),
            security_groups=[endpoint_sg],
        )

        
