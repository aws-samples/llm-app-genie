import logging
from dataclasses import dataclass
from typing import Sequence

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ssm as ssm
from constructs import Construct
from modules.stack import GenAiNestedStack, GenAiStack

stack = {
    "description": "VPC peering",
    "tags": {},
}


class VPCPeeringStack(GenAiNestedStack):
    # def __init__(self, scope: Construct, construct_id: str, config: Config, **kwargs) -> None:
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        peer_vpc_id: str,
        peer_vpc_cidr: str,
        peer_region: str,
        vpc_id: str,
        vpc_route_table_ids: Sequence[str],
        peering_connection_ssm_parameter_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        cfn_vPCPeering_connection = ec2.CfnVPCPeeringConnection(
            self,
            "VPCPeeringConnection",
            peer_vpc_id=peer_vpc_id,
            vpc_id=vpc_id,
            peer_region=peer_region,
        )

        ssm.StringParameter(
            self,
            "VPCPeeringParameter",
            parameter_name=peering_connection_ssm_parameter_name,
            description="Reference of VPC peering connection.",
            string_value=cfn_vPCPeering_connection.attr_id,
        )

        # peer_connection = cfn_bedrock_vPCPeering_connection

        # routes from the endpoint subnets to the peer vpc
        for index, rt_id in enumerate(vpc_route_table_ids):
            cfn_route = ec2.CfnRoute(
                self,
                f"RouteFromPeerVPC{index}",
                route_table_id=rt_id,
                destination_cidr_block=peer_vpc_cidr,
                vpc_peering_connection_id=cfn_vPCPeering_connection.ref,
            )
