import io
import os
import tempfile
import zipfile
from re import search
from unittest.mock import patch

import mock
from boto3 import client, resource, session
from moto import mock_iam, mock_lambda, mock_s3
from moto.core import DEFAULT_ACCOUNT_ID

from prowler.providers.aws.lib.audit_info.models import AWS_Audit_Info
from prowler.providers.aws.services.awslambda.awslambda_service import AuthType, Lambda
from prowler.providers.common.models import Audit_Metadata

# Mock Test Region
AWS_REGION = "eu-west-1"


def create_zip_file(code: str = "") -> io.BytesIO:
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
    if not code:
        zip_file.writestr(
            "lambda_function.py",
            """
            def lambda_handler(event, context):
                print("custom log event")
                return event
            """,
        )
    else:
        zip_file.writestr("lambda_function.py", code)
    zip_file.close()
    zip_output.seek(0)
    return zip_output


def mock_request_get(_):
    """Mock requests.get() to get the Lambda Code in Zip Format"""
    mock_resp = mock.MagicMock
    mock_resp.status_code = 200
    mock_resp.content = create_zip_file().read()
    return mock_resp


# Mock generate_regional_clients()
def mock_generate_regional_clients(service, audit_info):
    regional_client = audit_info.audit_session.client(service, region_name=AWS_REGION)
    regional_client.region = AWS_REGION
    return {AWS_REGION: regional_client}


@patch(
    "prowler.providers.aws.services.awslambda.awslambda_service.generate_regional_clients",
    new=mock_generate_regional_clients,
)
class Test_Lambda_Service:
    def set_mocked_audit_info(self):
        audit_info = AWS_Audit_Info(
            original_session=None,
            audit_session=session.Session(
                profile_name=None,
                botocore_session=None,
            ),
            audited_account=DEFAULT_ACCOUNT_ID,
            audited_user_id=None,
            audited_partition="aws",
            audited_identity_arn=None,
            profile=None,
            profile_region=None,
            credentials=None,
            assumed_role_info=None,
            audited_regions=None,
            organizations_metadata=None,
            audit_resources=None,
            audit_metadata=Audit_Metadata(
                services_scanned=0,
                # We need to set this check to call __list_functions__
                expected_checks=["awslambda_function_no_secrets_in_code"],
                completed_checks=0,
                audit_progress=0,
            ),
        )
        return audit_info

    # Test Lambda Client
    def test__get_client__(self):
        awslambda = Lambda(self.set_mocked_audit_info())
        assert awslambda.regional_clients[AWS_REGION].__class__.__name__ == "Lambda"

    # Test Lambda Session
    def test__get_session__(self):
        awslambda = Lambda(self.set_mocked_audit_info())
        assert awslambda.session.__class__.__name__ == "Session"

    # Test Lambda Service
    def test__get_service__(self):
        awslambda = Lambda(self.set_mocked_audit_info())
        assert awslambda.service == "lambda"

    @mock_lambda
    @mock_iam
    @mock_s3
    def test__list_functions__(self):
        # Create IAM Lambda Role
        iam_client = client("iam", region_name=AWS_REGION)
        iam_role = iam_client.create_role(
            RoleName="test-lambda-role",
            AssumeRolePolicyDocument="test-policy",
            Path="/",
        )["Role"]["Arn"]
        # Create S3 Bucket
        s3_client = resource("s3", region_name=AWS_REGION)
        s3_client.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
        )
        # Create Test Lambda
        lambda_client = client("lambda", region_name=AWS_REGION)
        lambda_name = "test-lambda"
        resp = lambda_client.create_function(
            FunctionName=lambda_name,
            Runtime="python3.7",
            Role=iam_role,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": create_zip_file().read()},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            PackageType="ZIP",
            Publish=True,
            VpcConfig={
                "SecurityGroupIds": ["sg-123abc"],
                "SubnetIds": ["subnet-123abc"],
            },
            Environment={"Variables": {"db-password": "test-password"}},
        )
        # Update Lambda Policy
        lambda_policy = {
            "Version": "2012-10-17",
            "Id": "default",
            "Statement": [
                {
                    "Action": "lambda:GetFunction",
                    "Principal": "*",
                    "Effect": "Allow",
                    "Resource": f"arn:aws:lambda:{AWS_REGION}:{DEFAULT_ACCOUNT_ID}:function:{lambda_name}",
                    "Sid": "test",
                }
            ],
        }
        _ = lambda_client.add_permission(
            FunctionName=lambda_name,
            StatementId="test",
            Action="lambda:GetFunction",
            Principal="*",
        )
        # Create Function URL Config
        _ = lambda_client.create_function_url_config(
            FunctionName=lambda_name,
            AuthType=AuthType.AWS_IAM.value,
            Cors={
                "AllowCredentials": True,
                "AllowHeaders": [
                    "string",
                ],
                "AllowMethods": [
                    "string",
                ],
                "AllowOrigins": [
                    "*",
                ],
                "ExposeHeaders": [
                    "string",
                ],
                "MaxAge": 123,
            },
        )

        lambda_arn = resp["FunctionArn"]
        with mock.patch(
            "prowler.providers.aws.services.awslambda.awslambda_service.requests.get",
            new=mock_request_get,
        ):
            awslambda = Lambda(self.set_mocked_audit_info())

            assert awslambda.functions
            assert awslambda.functions[lambda_name].name == lambda_name
            assert awslambda.functions[lambda_name].arn == lambda_arn
            assert awslambda.functions[lambda_name].runtime == "python3.7"
            assert awslambda.functions[lambda_name].environment == {
                "db-password": "test-password"
            }
            assert awslambda.functions[lambda_name].region == AWS_REGION
            assert awslambda.functions[lambda_name].policy == lambda_policy

            assert awslambda.functions[lambda_name].code
            assert search(
                f"s3://awslambda-{AWS_REGION}-tasks.s3-{AWS_REGION}.amazonaws.com",
                awslambda.functions[lambda_name].code.location,
            )

            assert awslambda.functions[lambda_name].url_config
            assert (
                awslambda.functions[lambda_name].url_config.auth_type
                == AuthType.AWS_IAM
            )
            assert search(
                "lambda-url.eu-west-1.on.aws",
                awslambda.functions[lambda_name].url_config.url,
            )

            assert awslambda.functions[lambda_name].url_config.cors_config
            assert awslambda.functions[
                lambda_name
            ].url_config.cors_config.allow_origins == ["*"]

            # Pending ZipFile tests
            with tempfile.TemporaryDirectory() as tmp_dir_name:
                awslambda.functions[lambda_name].code.code_zip.extractall(tmp_dir_name)
                files_in_zip = next(os.walk(tmp_dir_name))[2]
                assert len(files_in_zip) == 1
                assert files_in_zip[0] == "lambda_function.py"
                with open(f"{tmp_dir_name}/{files_in_zip[0]}", "r") as lambda_code_file:
                    _ = lambda_code_file
                    # assert (
                    #     lambda_code_file.read()
                    #     == """
                    # def lambda_handler(event, context):
                    # print("custom log event")
                    # return event
                    # """
                    # )
