from dataclasses import dataclass


@dataclass
class AWSConfig:
    account_id: str
    """ AWS account id """
    region: str
    """ AWS region"""
