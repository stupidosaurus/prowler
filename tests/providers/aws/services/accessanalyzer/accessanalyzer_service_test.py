from unittest.mock import patch

import botocore

from prowler.providers.aws.lib.audit_info.audit_info import current_audit_info
from prowler.providers.aws.services.accessanalyzer.accessanalyzer_service import (
    AccessAnalyzer,
)

# Mock Test Region
AWS_REGION = "eu-west-1"

# Mocking Access Analyzer Calls
make_api_call = botocore.client.BaseClient._make_api_call


def mock_make_api_call(self, operation_name, kwarg):
    """
    Mock every AWS API call using Boto3

    As you can see the operation_name has the list_analyzers snake_case form but
    we are using the ListAnalyzers form.
    Rationale -> https://github.com/boto/botocore/blob/develop/botocore/client.py#L810:L816
    """
    if operation_name == "ListAnalyzers":
        return {
            "analyzers": [
                {
                    "arn": "ARN",
                    "name": "Test Analyzer",
                    "status": "Enabled",
                    "findings": 0,
                    "tags": "",
                    "type": "ACCOUNT",
                    "region": "eu-west-1",
                }
            ]
        }
    if operation_name == "ListFindings":
        # If we only want to count the number of findings
        # we return a list of values just to count them
        return {
            "findings": [
                {
                    "id": "test_id1",
                }
            ]
        }
    if operation_name == "GetFinding":
        # If we only want to count the number of findings
        # we return a list of values just to count them
        return {"finding": {"id": "test_id1", "status": "ARCHIVED"}}
    return make_api_call(self, operation_name, kwarg)


def mock_generate_regional_clients(service, audit_info):
    regional_client = audit_info.audit_session.client(service, region_name=AWS_REGION)
    regional_client.region = AWS_REGION
    return {AWS_REGION: regional_client}


# Patch every AWS call using Boto3 and generate_regional_clients to have 1 client
@patch("botocore.client.BaseClient._make_api_call", new=mock_make_api_call)
@patch(
    "prowler.providers.aws.services.accessanalyzer.accessanalyzer_service.generate_regional_clients",
    new=mock_generate_regional_clients,
)
class Test_AccessAnalyzer_Service:
    # Test AccessAnalyzer Client
    def test__get_client__(self):
        access_analyzer = AccessAnalyzer(current_audit_info)
        assert (
            access_analyzer.regional_clients[AWS_REGION].__class__.__name__
            == "AccessAnalyzer"
        )

    # Test AccessAnalyzer Session
    def test__get_session__(self):
        access_analyzer = AccessAnalyzer(current_audit_info)
        assert access_analyzer.session.__class__.__name__ == "Session"

    # Test AccessAnalyzer Service
    def test__get_service__(self):
        access_analyzer = AccessAnalyzer(current_audit_info)
        assert access_analyzer.service == "accessanalyzer"

    def test__list_analyzers__(self):
        # Set partition for the service
        current_audit_info.audited_partition = "aws"
        access_analyzer = AccessAnalyzer(current_audit_info)
        assert len(access_analyzer.analyzers) == 1
        assert access_analyzer.analyzers[0].arn == "ARN"
        assert access_analyzer.analyzers[0].name == "Test Analyzer"
        assert access_analyzer.analyzers[0].status == "Enabled"
        assert access_analyzer.analyzers[0].tags == ""
        assert access_analyzer.analyzers[0].type == "ACCOUNT"
        assert access_analyzer.analyzers[0].region == AWS_REGION

    def test__list_findings__(self):
        # Set partition for the service
        current_audit_info.audited_partition = "aws"
        access_analyzer = AccessAnalyzer(current_audit_info)
        assert len(access_analyzer.analyzers) == 1
        assert len(access_analyzer.analyzers[0].findings) == 1
        assert access_analyzer.analyzers[0].findings[0].status == "ARCHIVED"
        assert access_analyzer.analyzers[0].findings[0].id == "test_id1"
