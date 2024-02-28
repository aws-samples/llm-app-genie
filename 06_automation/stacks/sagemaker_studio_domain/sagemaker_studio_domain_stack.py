# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import aws_cdk.aws_sagemaker as sagemaker
from constructs import Construct
from modules.stack import GenAiStack
from modules.config import config

stack = {"description": "Sagemaker Studio Domain"}


class SageMakerStudioStack(GenAiStack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        secrets_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ssm:GetParameters", "ssm:GetParameter"],
                    resources=[
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter/{config['appPrefix']}HfPredictorEndpointName",
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter/{config['appPrefix']}OpenSearchDomainName",
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter/{config['appPrefix']}OpenSearchEndpoint",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["secretsmanager:ListSecrets"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "secretsmanager:GetResourcePolicy",
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret",
                        "secretsmanager:ListSecretVersionIds",
                    ],
                    resources=[
                        f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{config['appPrefix']}OpenSearchCredentials*"
                    ],
                ),
            ]
        )
        # Create a SageMaker
        role_sagemaker_studio_domain = iam.Role(
            self,
            "RoleForSagemakerStudioUsers",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonOpenSearchServiceFullAccess"
                ),  # in ingest and create indexes
            ],
            inline_policies={"parametersAndSecrets": secrets_policy},
        )

        team = config['appPrefix'] + "DataScientist"
        sagemaker_domain_name = config['appPrefix'] + "SagemakerStudio"

        default_vpc = ec2.Vpc.from_lookup(self, id="VPC", is_default=True)
        public_subnet_ids = [
            public_subnet.subnet_id for public_subnet in default_vpc.public_subnets
        ]

        my_sagemaker_domain = sagemaker.CfnDomain(
            self,
            "SageMakerStudioDomain",
            auth_mode="IAM",
            default_user_settings=sagemaker.CfnDomain.UserSettingsProperty(
                execution_role=role_sagemaker_studio_domain.role_arn
            ),
            domain_name=sagemaker_domain_name,
            subnet_ids=public_subnet_ids,
            vpc_id=default_vpc.vpc_id,
            app_network_access_type="VpcOnly",
            app_security_group_management="Service"
        )

        sagemaker.CfnUserProfile(
            self,
            "CfnUserProfile",
            domain_id=my_sagemaker_domain.attr_domain_id,
            user_profile_name=team,
            user_settings=sagemaker.CfnUserProfile.UserSettingsProperty(
                execution_role=role_sagemaker_studio_domain.role_arn
            ),
        )
