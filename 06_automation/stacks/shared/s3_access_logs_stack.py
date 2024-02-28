
from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_s3 as s3
from constructs import Construct
from modules.stack import GenAiNestedStack

stack = {
    "description": "Substack for S3 access logs",
    "tags": {},
}


class S3AccessLogsStack(GenAiNestedStack):

    bucket: s3.Bucket
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        access_logs_lifecycle_rule = s3.LifecycleRule(
            id="S3AccessLogsBucketLifecycleRule",
            abort_incomplete_multipart_upload_after=Duration.days(1),
            enabled=True,
            expiration=Duration.days(30),
          #  expired_object_delete_marker=True,
            noncurrent_version_expiration=Duration.days(90),
            noncurrent_versions_to_retain=123,
            noncurrent_version_transitions=[s3.NoncurrentVersionTransition(
                storage_class=s3.StorageClass.GLACIER,
                transition_after=Duration.days(7),

                # the properties below are optional
                #noncurrent_versions_to_retain=123
            )],
            transitions=[s3.Transition(
                storage_class=s3.StorageClass.GLACIER,

                transition_after=Duration.days(14),
            )]
        )
        
        access_logs_bucket = s3.Bucket(self, "AccessLogsBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[access_logs_lifecycle_rule]
        )

        self.bucket = access_logs_bucket

