from unittest.mock import patch

import botocore

from prowler.providers.aws.lib.audit_info.audit_info import current_audit_info
from prowler.providers.aws.services.securityhub.securityhub_service import SecurityHub

# Mock Test Region
AWS_REGION = "eu-west-1"

# Mocking Access Analyzer Calls
make_api_call = botocore.client.BaseClient._make_api_call


def mock_make_api_call(self, operation_name, kwarg):
    """
    We have to mock every AWS API call using Boto3

    As you can see the operation_name has the snake_case
    Rationale -> https://github.com/boto/botocore/blob/develop/botocore/client.py#L810:L816
    """
    if operation_name == "GetEnabledStandards":
        return {
            "StandardsSubscriptions": [
                {
                    "StandardsArn": "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0",
                    "StandardsSubscriptionArn": "arn:aws:securityhub:us-east-1:0123456789012:subscription/cis-aws-foundations-benchmark/v/1.2.0",
                    "StandardsInput": {"string": "string"},
                    "StandardsStatus": "READY",
                },
            ]
        }
    if operation_name == "ListEnabledProductsForImport":
        return {
            "ProductSubscriptions": [
                "arn:aws:securityhub:us-east-1:0123456789012:product-subscription/prowler/prowler",
            ]
        }
    if operation_name == "DescribeHub":
        return {
            "HubArn": "arn:aws:securityhub:us-east-1:0123456789012:hub/default",
        }
    return make_api_call(self, operation_name, kwarg)


# Mock generate_regional_clients()
def mock_generate_regional_clients(service, audit_info):
    regional_client = audit_info.audit_session.client(service, region_name=AWS_REGION)
    regional_client.region = AWS_REGION
    return {AWS_REGION: regional_client}


# Patch every AWS call using Boto3 and generate_regional_clients to have 1 client
@patch("botocore.client.BaseClient._make_api_call", new=mock_make_api_call)
@patch(
    "prowler.providers.aws.services.securityhub.securityhub_service.generate_regional_clients",
    new=mock_generate_regional_clients,
)
class Test_SecurityHub_Service:
    # Test SecurityHub Client
    def test__get_client__(self):
        access_analyzer = SecurityHub(current_audit_info)
        assert (
            access_analyzer.regional_clients[AWS_REGION].__class__.__name__
            == "SecurityHub"
        )

    # Test SecurityHub Session
    def test__get_session__(self):
        access_analyzer = SecurityHub(current_audit_info)
        assert access_analyzer.session.__class__.__name__ == "Session"

    def test__describe_hub__(self):
        # Set partition for the service
        current_audit_info.audited_partition = "aws"
        securityhub = SecurityHub(current_audit_info)
        assert len(securityhub.securityhubs) == 1
        assert (
            securityhub.securityhubs[0].arn
            == "arn:aws:securityhub:us-east-1:0123456789012:hub/default"
        )
        assert securityhub.securityhubs[0].id == "default"
        assert securityhub.securityhubs[0].standards == "cis-aws-foundations-benchmark "
        assert securityhub.securityhubs[0].integrations == "prowler "
