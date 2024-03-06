"""
    Lambda function that implements a CloudFormation custom resource that
    Generates and registers a self-signed certificate into ACM.
"""
from OpenSSL import crypto
from cryptography import x509
import boto3
import hashlib

acm = boto3.client("acm")

identifier_tag_key = 'CDK_CUSTOM_RESOURCE_DONT_DELETE_IDENTIFIER'

def lambda_handler(event, context):
    """
    Lambda function handler that implements the actions when CloudFormation
    requests a resource Create/Update/Delete.
    """
    props = event["ResourceProperties"]
    request_type = event["RequestType"]
    stack_id = event["StackId"]
    tags = props["tags"]


    identifier = get_identifier(**props)

    if request_type == "Create":
        cert = generate_certificate(**props)
        cert_arn = register_certificate_in_acm(cert=cert, stack_id=stack_id, tags=tags, id=identifier)
    elif request_type == "Update":
        # Deletes and regenerates a self-signed certificate
        cert_arn = event["PhysicalResourceId"]
        existing_identifier = get_identifier_of(cert_arn)

        if identifier != existing_identifier:
            # Need to replace certificate
            cert_arn = delete_certificate()
            cert = generate_certificate(**props)
            cert_arn = register_certificate_in_acm(cert=cert, stack_id=stack_id, tags=tags, id=identifier )
    else: # Delete
        cert_arn = delete_certificate(event["PhysicalResourceId"])

    output = {
        'PhysicalResourceId': cert_arn,
        'Data': {
            'CertificateArn': cert_arn
        }
    }

    return output

def generate_certificate(
        email_address,
        common_name,
        country_code,
        city,
        state,
        organization,
        organizational_unit,
        validity_seconds: int=5*365*24*60*60, # Five years validity
        **kwargs
    ):
    """
    Generates a self-signed x509 certificate with a random serial number.
    Returns the private key and certificate as byte arrays.
    """
    # Create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 4096)

    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = country_code
    cert.get_subject().ST = state
    cert.get_subject().L = city
    cert.get_subject().O = organization
    cert.get_subject().OU = organizational_unit
    cert.get_subject().CN = common_name
    cert.get_subject().emailAddress = email_address
    cert.set_serial_number(x509.random_serial_number())
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(int(validity_seconds))
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha512')

    return {
        "private_key": crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8"),
        "certificate": crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8"),
    }

def get_identifier(
        email_address,
        common_name,
        country_code,
        city,
        state,
        organization,
        organizational_unit,
        validity_seconds: int=5*365*24*60*60, # Five years validity
        **kwargs):
    """
    Creates a string identifier for the config of the certificate configuration.
    """
    config = email_address + common_name + country_code + city + state + organization + organizational_unit + validity_seconds
    cert_hash = hashlib.sha256(config.encode("utf-8"), usedforsecurity=False ).hexdigest()
    return cert_hash

def register_certificate_in_acm(cert, stack_id, tags: dict[str, str], id: str):
    """
    Registers the input x509 certificate into ACM and returns its ARN
    """
    private_key = cert["private_key"]
    certificate = cert["certificate"]

    tags.append(
        {
            'Key': identifier_tag_key,
            'Value': id
        }
    )

    tags.append(
        {
            'Key': "stack-id",
            'Value': stack_id
        }
    )
    result = acm.import_certificate(
        Certificate=certificate,
        PrivateKey=private_key,
        Tags=tags
    )

    return result['CertificateArn']

def delete_certificate(cert_arn):
    """
    Deletes the certificate from ACM
    """
    acm.delete_certificate(CertificateArn=cert_arn)

    return cert_arn

def get_identifier_of(cert_arn):
    """
    Gets the identifier from the tags of an existing cert
    """
    all_tags = acm.list_tags_for_certificate(CertificateArn=cert_arn)
    filtered_tags = [tag['Value'] for tag in all_tags['Tags'] if tag['Key'] == identifier_tag_key]
    identifier_tag = next(filtered_tags, [None] )

    return identifier_tag

