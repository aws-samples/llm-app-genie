import json

from aws_cdk import Duration, RemovalPolicy, Tags, CustomResource
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr_assets
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_iam as iam
from aws_cdk import aws_secretsmanager as sm
from aws_cdk import aws_lambda_python_alpha as lambda_python
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import custom_resources as cr

from constructs import Construct
from modules.config import config
from modules.stack import GenAiStack

stack = {
    "description": "Generative AI Chatbot Application",
    "tags": {},
}


class ChatbotStack(GenAiStack):
    # def __init__(self, scope: Construct, construct_id: str, config: Config, **kwargs) -> None:
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        cert_function = lambda_python.PythonFunction(
            self, "RegisterSelfSignedCert",
            entry="./stacks/chatbot/cert_lambda",
            index="function.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(amount=120)
        )

        cert_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["acm:ImportCertificate"],
                resources=["*"]
            )
        )

        # list_tags_keys = [t.key() for t in Tags.of(self)]
        # print(list_tags_keys)
        cert_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["acm:AddTagsToCertificate"],
                resources=["*"]
            )
        )

        provider = cr.Provider(
            self, "self_signed_cert_custom_resource_provider",
            on_event_handler=cert_function
        )

        custom_resource = CustomResource(
            self, "self_signed_cert_custom_resource",
            service_token=provider.service_token,
            properties={
                "email_address": config['self_signed_certificate']['email_address'],
                "common_name": config['self_signed_certificate']['common_name'],
                "city": config['self_signed_certificate']['city'],
                "state": config['self_signed_certificate']['state'],
                "country_code": config['self_signed_certificate']['country_code'],
                "organization": config['self_signed_certificate']['organization'],
                "organizational_unit": config['self_signed_certificate']['organizational_unit'],
                "validity_seconds": config['self_signed_certificate']['validity_seconds']
            }
        )

        cert_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["acm:DeleteCertificate"],
                resources=["*"],
            )
        )

        certificate = acm.Certificate.from_certificate_arn(
            self,
            id="self_signed_cert",
            certificate_arn=custom_resource.ref
        )

        # The code that defines your stack goes here

        cluster_name = "gen-ai-cluster"
        service_name = "gen-ai-service"

        public_subnet = ec2.SubnetConfiguration(
            name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
        )
        private_subnet = ec2.SubnetConfiguration(
            name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24
        )

        vpc = ec2.Vpc(
            scope=self,
            id="gen-ai-vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            nat_gateway_provider=ec2.NatProvider.gateway(),
            nat_gateways=1,
            subnet_configuration=[public_subnet, private_subnet],
        )

        memory_table = dynamodb.Table(
            self,
            "MemoryTable",
            partition_key=dynamodb.Attribute(
                name="SessionId", type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        Tags.of(memory_table).add(
            f"{config['appPrefixLC']}:memory-table",
            "Use this table to store the history",
        )

        # ==================================================
        # =============== STREAMLIT CREDENTIALS ============
        # ==================================================
        cdk_streamlit_pw = sm.Secret(
            scope=self,
            id="streamlit_credentials",
            secret_name="streamlit_credentials",
            generate_secret_string=sm.SecretStringGenerator(
                secret_string_template=json.dumps({"username": "admin"}),
                generate_string_key="password",
                password_length=10,
                exclude_punctuation=True,
            ),
        )

        # ==================================================
        # ========== IAM ROLE for the ECS task =============
        # ==================================================
        role = iam.Role(
            scope=self,
            id="TASKROLE",
            assumed_by=iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
        )
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonECS_FullAccess")
        )
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonEC2ContainerRegistryReadOnly"
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sagemaker:InvokeEndpoint", "sagemaker:DescribeEndpoint"],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/*"
                ],
                conditions={
                    "StringEquals": {"aws:ResourceTag/gena:deployment": "True"}
                },
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW, actions=["sagemaker:List*"], resources=["*"]
            )
        )
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "SecretsManagerReadWrite"
            )  # is this still necessary?
        )
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kendra:Query", "kendra:ListTagsForResource"],
                resources=[f"arn:aws:kendra:{self.region}:{self.account}:index/*"],
            )
        )
        # Policy to allow listing Kendra indices
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kendra:ListIndices", "kendra:ListDataSources"],
                resources=["*"],
            )
        )
        # Policy statement to allow querying the Kendra indices that have the gena:deployment tag
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kendra:Query", "kendra:Retrieve"],
                resources=[f"arn:aws:kendra:{self.region}:{self.account}:index/*"],
                conditions={
                    "StringEquals": {"aws:ResourceTag/gena:deployment": "True"}
                },
            )
        )
        # Policy statement to grant access to Amazon Bedrock
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW, actions=["bedrock:*"], resources=["*"]
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["es:ListDomainNames"],
                resources=["*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "es:DescribeElasticsearchDomains",
                    "es:ListTags",
                ],
                resources=[
                    f"arn:aws:es:{self.region}:{self.account}:domain/*",
                    f"arn:aws:es:{config['bedrock_region']}:{self.account}:domain/*",  ## must be fixed
                ],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:List*",
                    "dynamodb:DescribeReservedCapacity*",
                    "dynamodb:DescribeLimits",
                    "dynamodb:DescribeTimeToLive",
                ],
                resources=["*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:BatchGet*",
                    "dynamodb:DescribeStream",
                    "dynamodb:DescribeTable",
                    "dynamodb:Get*",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWrite*",
                    "dynamodb:CreateTable",
                    "dynamodb:Delete*",
                    "dynamodb:Update*",
                    "dynamodb:PutItem",
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/{memory_table.table_name}"
                ],
            )
        )

        # ==================================================
        # =============== FARGATE SERVICE ==================
        # ==================================================
        cluster = ecs.Cluster(
            scope=self, id="CLUSTER", cluster_name=cluster_name, vpc=vpc
        )

        task_definition = ecs.FargateTaskDefinition(
            scope=self,
            id="streamlit-chatbot",
            task_role=role,
            cpu=2 * 1024,
            memory_limit_mib=4 * 1024,
        )

        # Do not use a port lower than 1024. The container image runs the app as non root user. Non root user cannot bind to port lower than 1024 in ECS.
        container_port = 3001

        container = task_definition.add_container(
            id="streamit-container",
            image=ecs.ContainerImage.from_asset(
                directory="../03_chatbot",
                platform=aws_ecr_assets.Platform.LINUX_AMD64,
                build_args={"LISTEN_PORT": str(container_port)},
            ),
            logging=ecs.LogDriver.aws_logs(stream_prefix="gen-ai-app"),
            environment={
                "REGION": self.region,
                "AWS_DEFAULT_REGION": self.region,
                "BEDROCK_REGION": config["bedrock_region"],
            },
            secrets={
                "PASSWORD": ecs.Secret.from_secrets_manager(cdk_streamlit_pw, 'password'),
                "USERNAME": ecs.Secret.from_secrets_manager(cdk_streamlit_pw, 'username')
            },
            health_check=ecs.HealthCheck(
                command=[
                    "CMD-SHELL",
                    f"curl --fail http://localhost:{container_port}/_stcore/health",
                ],
            ),
        )

        port_mapping = ecs.PortMapping(
            container_port=container_port,
            host_port=container_port,
            protocol=ecs.Protocol.TCP,
        )
        container.add_port_mappings(port_mapping)

        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            scope=self,
            id="Gen-AI",
            service_name=service_name,
            cluster=cluster,
            task_definition=task_definition,
            certificate=certificate
        )

        # Setup security group
        fargate_service.service.connections.security_groups[0].add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(container_port),
            description="Allow inbound from VPC for gen-ai-app",
        )

        # Setup autoscaling policy
        scaling = fargate_service.service.auto_scale_task_count(
            max_capacity=2
        )  # figure out autscaling metrics
        scaling.scale_on_cpu_utilization(
            id="AUTOSCALING",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )
