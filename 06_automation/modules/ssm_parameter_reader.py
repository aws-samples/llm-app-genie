from dataclasses import dataclass
from datetime import datetime

from aws_cdk import custom_resources as custom_rsrc
from constructs import Construct


@dataclass
class SSMParameterReaderProps:
    parameter_name: str
    region: str


class SSMParameterReader(custom_rsrc.AwsCustomResource):
    def __init__(
        self, scope: Construct, id: str, props: SSMParameterReaderProps
    ) -> None:
        ssm_aws_sdk_call = custom_rsrc.AwsSdkCall(
            service="SSM",
            action="getParameter",
            parameters={"Name": props.parameter_name},
            region=props.region,
            physical_resource_id=custom_rsrc.PhysicalResourceId.of(str(datetime.now())),
        )

        super().__init__(
            scope,
            id,
            on_update=ssm_aws_sdk_call,
            policy=custom_rsrc.AwsCustomResourcePolicy.from_sdk_calls(
                resources=custom_rsrc.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
        )

    def get_parameter_value(self) -> str:
        return self.get_response_field("Parameter.Value")
