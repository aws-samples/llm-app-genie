import json
from typing import Union

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
from constructs import Construct
from modules.config import config
from modules.stack import GenAiStack
from ..shared.s3_access_logs_stack import S3AccessLogsStack

stack = {
    "description": "Generative AI Chatbot Application",
    "tags": {},
}


class ChatbotStack(GenAiStack):

    chatbot_security_group: ec2.ISecurityGroup

    # def __init__(self, scope: Construct, construct_id: str, config: Config, **kwargs) -> None:
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)



        # Do not use a port lower than 1024. The container image runs the app as non root user. Non root user cannot bind to port lower than 1024 in ECS.
        self.container_port = 3001
        self.port_mapping = ecs.PortMapping(
            container_port=self.container_port,
            host_port=self.container_port,
            protocol=ecs.Protocol.TCP,
        )

        cert_function = lambda_python.PythonFunction(
            self,
            "RegisterSelfSignedCert",
            entry="./stacks/chatbot/cert_lambda",
            index="function.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(amount=120),
        )

        provider = cr.Provider(
            self, "SelfSignedCertCustomResourceProvider", on_event_handler=cert_function
        )

        provider.node.add_dependency(cert_function)


        
        all_tags = config["globalTags"] | stack["tags"]
        custom_resource_tags = [{'Key': k, 'Value': v} for k, v in all_tags.items()]
        

        certificate_conditional_tag = {
            "Key": f"{config['appPrefix']}:CDK_DONT_DELETE",
            "Value":Names.unique_id(provider)
        }
        custom_resource_tags.append(certificate_conditional_tag)

        cert_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["acm:ImportCertificate"],
                resources=["*"],
                conditions=
                    {
                    "StringEquals": {f"aws:ResourceTag/{certificate_conditional_tag['Key']}": certificate_conditional_tag['Value']}
                }
                
            )
        )

        cert_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["acm:AddTagsToCertificate"], resources=["*"],
                conditions=
                    {
                    "StringEquals": {f"aws:ResourceTag/{certificate_conditional_tag['Key']}": certificate_conditional_tag['Value']}
                    }
                
            )
        )

        

        custom_resource = CustomResource(
            self,
            "SelfSignedCertCustomResource",
            service_token=provider.service_token,
            properties={
                "email_address": config["self_signed_certificate"]["email_address"],
                "common_name": config["self_signed_certificate"]["common_name"],
                "city": config["self_signed_certificate"]["city"],
                "state": config["self_signed_certificate"]["state"],
                "country_code": config["self_signed_certificate"]["country_code"],
                "organization": config["self_signed_certificate"]["organization"],
                "organizational_unit": config["self_signed_certificate"][
                    "organizational_unit"
                ],
                "validity_seconds": config["self_signed_certificate"][
                    "validity_seconds"
                ],
                "tags":  custom_resource_tags,
            },
        )

        custom_resource.node.add_dependency(provider)

        cert_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["acm:DeleteCertificate"],
                resources=["*"],
                conditions={
                    "StringEquals": {f"aws:ResourceTag/{certificate_conditional_tag['Key']}": certificate_conditional_tag['Value']}
                },
            )
        )

        

        certificate = acm.Certificate.from_certificate_arn(
            self, id="SelfSignedCert", certificate_arn=custom_resource.ref
        )

        certificate.node.add_dependency(custom_resource)

        memory_table = dynamodb.Table(
            self,
            "MemoryTable",
            partition_key=dynamodb.Attribute(
                name="SessionId", type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True
        )

        textract_bucket = s3.Bucket(
            self,
            f"TextractBucket",
            versioned=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        Tags.of(memory_table).add(
            f"genie:memory-table",
            "Use this table to store the history",
        )

        # ==================================================
        # =============== STREAMLIT CREDENTIALS ============
        # ==================================================
        cdk_streamlit_pw = sm.Secret(
            scope=self,
            id="StreamlitCredentials",
            secret_name=config["appPrefix"] + "StreamlitCredentials",
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
            id="Taskrole",
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
                    "StringEquals": {f"aws:ResourceTag/genie:deployment": "True"}
                }
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
        # Policy statement to allow querying the Kendra indices that have the genie:deployment tag
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kendra:Query", "kendra:Retrieve"],
                resources=[f"arn:aws:kendra:{self.region}:{self.account}:index/*"],
                conditions={
                      "StringEquals": {f"aws:ResourceTag/genie:deployment": "True"}
                },
            )
        )
        # Policy statement to grant access to Amazon Bedrock
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:ListFoundationModels",
                    "bedrock:GetFoundationModel",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:ListTagsForResource",
                ],
                resources=["*"],
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
                    #"dynamodb:Delete*",
                    "dynamodb:DeleteItem",
                    "dynamodb:Update*",
                    "dynamodb:PutItem",
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/{memory_table.table_name}"
                ],
            )
        )

        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListObject",
                    "s3:PutObject",
                    "s3:DeleteObject"
                ],
                resources=[
                    f"arn:aws:s3:::{textract_bucket.bucket_name}",
                    f"arn:aws:s3:::{textract_bucket.bucket_name}/*"
                ]
            )
        )

        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "textract:DetectDocumentText",
                    "textract:AnalyzeDocument",
                    "textract:StartDocumentAnalysis",
                    "textract:GetDocumentAnalysis"
                ],
                resources=["*"]
            )
        )

        # ==================================================
        # =============== FARGATE SERVICE ==================
        # ==================================================
        cluster = ecs.Cluster(scope=self, id="Cluster", vpc=vpc, container_insights=True)

        task_definition = ecs.FargateTaskDefinition(
            scope=self,
            id=config["appPrefix"] + "StreamlitChatbot",
            task_role=role,
            cpu=2 * 1024,
            memory_limit_mib=4 * 1024,
        )

        container = task_definition.add_container(
            id=config["appPrefix"] + "StreamitContainer",
            image=ecs.ContainerImage.from_asset(
                directory="../03_chatbot",
                platform=aws_ecr_assets.Platform.LINUX_AMD64,
                build_args={"LISTEN_PORT": str(self.container_port)},
            ),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix=config["appPrefixLowerCase"] + "-ai-app"
            ),
            environment={
                "REGION": self.region,
                "AWS_DEFAULT_REGION": self.region,
                "BEDROCK_REGION": config["bedrock_region"],
                "AMAZON_TEXTRACT_S3_BUCKET": textract_bucket.bucket_name,
                "APP_PREFIX": config["appPrefix"]
            },
            secrets={
                "PASSWORD": ecs.Secret.from_secrets_manager(
                    cdk_streamlit_pw, "password"
                ),
                "USERNAME": ecs.Secret.from_secrets_manager(
                    cdk_streamlit_pw, "username"
                ),
            },
            health_check=ecs.HealthCheck(
                command=[
                    "CMD-SHELL",
                    f"curl --fail http://localhost:{self.container_port}/_stcore/health",
                ],
            ),
        )

        container.add_port_mappings(self.port_mapping)

        fargate_service_sg = ec2.SecurityGroup(
            self,
            "ChatbotFargateServiceSecurityGroup",
            vpc=vpc,
            description="Chatbot service security group",
            allow_all_outbound=False,
            disable_inline_rules=True,
        )

        # Set up security group rules for chatbot service running on Fargate.
        # Note the ApplicationLoadBalancedFargateService construct takes care
        # of connectivity between the load balancer and service.
        # Allow outbound connections to connect to AWS service like SecretsManager
        fargate_service_sg.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow outbound HTTPS connections",
        )


        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            scope=self,
            id="Service",
            cluster=cluster,
            task_definition=task_definition,
            certificate=certificate,
            security_groups=[fargate_service_sg],
        )

        fargate_service.listener.node.add_dependency(custom_resource)
        fargate_service.listener.node.add_dependency(certificate)
        fargate_service.listener.node.add_dependency(cert_function)
        fargate_service.listener.node.add_dependency(provider)


        
        service_connectable = fargate_service.service.connections

        self.chatbot_security_group = service_connectable.connections.security_groups[0]
        # Setup service security group
        service_connectable.allow_to_any_ipv4(
            port_range=ec2.Port.tcp(443), description="Allow HTTPS to internet"
        )

        service_connectable.allow_from(
            ec2.Peer.ipv4(vpc.vpc_cidr_block),
            port_range=ec2.Port.tcp(self.container_port),
            description=f"Allow inbound from VPC for {config['appPrefixLowerCase']}-ai-app",
        )

        s3_access_logs = S3AccessLogsStack(
            scope=self,
            construct_id="ChatbotAccessLogsStack"
        )
        # Enable access logging
        fargate_service.load_balancer.log_access_logs(
            bucket=s3_access_logs.bucket
        )

        # Setup autoscaling policy
        scaling = fargate_service.service.auto_scale_task_count(
            max_capacity=2
        )  # figure out autscaling metrics
        scaling.scale_on_cpu_utilization(
            id="Autoscaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )
