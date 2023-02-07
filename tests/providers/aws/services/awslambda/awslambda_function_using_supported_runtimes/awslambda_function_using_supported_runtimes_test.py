from unittest import mock

from moto.core import DEFAULT_ACCOUNT_ID

from prowler.providers.aws.services.awslambda.awslambda_service import Function

AWS_REGION = "us-east-1"


def mock_get_config_var(config_var: str):
    return [
        "python3.6",
        "python2.7",
        "nodejs4.3",
        "nodejs4.3-edge",
        "nodejs6.10",
        "nodejs",
        "nodejs8.10",
        "nodejs10.x",
        "dotnetcore1.0",
        "dotnetcore2.0",
        "dotnetcore2.1",
        "ruby2.5",
    ]


class Test_awslambda_function_using_supported_runtimes:
    def test_no_functions(self):
        lambda_client = mock.MagicMock
        lambda_client.functions = {}

        with mock.patch(
            "prowler.providers.aws.services.awslambda.awslambda_service.Lambda",
            new=lambda_client,
        ):
            # Test Check
            from prowler.providers.aws.services.awslambda.awslambda_function_using_supported_runtimes.awslambda_function_using_supported_runtimes import (
                awslambda_function_using_supported_runtimes,
            )

            check = awslambda_function_using_supported_runtimes()
            result = check.execute()

            assert len(result) == 0

    def test_function_obsolete_runtime(self):
        lambda_client = mock.MagicMock
        function_name = "test-lambda"
        function_runtime = "nodejs4.3"
        function_arn = (
            f"arn:aws:lambda:{AWS_REGION}:{DEFAULT_ACCOUNT_ID}:function/{function_name}"
        )
        lambda_client.functions = {
            "function_name": Function(
                name=function_name,
                arn=function_arn,
                region=AWS_REGION,
                runtime=function_runtime,
            )
        }

        with mock.patch(
            "prowler.providers.aws.services.awslambda.awslambda_service.Lambda",
            new=lambda_client,
        ), mock.patch(
            "prowler.providers.aws.services.awslambda.awslambda_function_using_supported_runtimes.awslambda_function_using_supported_runtimes.get_config_var",
            new=mock_get_config_var,
        ):
            # Test Check
            from prowler.providers.aws.services.awslambda.awslambda_function_using_supported_runtimes.awslambda_function_using_supported_runtimes import (
                awslambda_function_using_supported_runtimes,
            )

            check = awslambda_function_using_supported_runtimes()
            result = check.execute()

            assert len(result) == 1
            assert result[0].region == AWS_REGION
            assert result[0].resource_id == function_name
            assert result[0].resource_arn == function_arn
            assert result[0].status == "FAIL"
            assert (
                result[0].status_extended
                == f"Lambda function {function_name} is using {function_runtime} which is obsolete"
            )

    def test_function_supported_runtime(self):
        lambda_client = mock.MagicMock
        function_name = "test-lambda"
        function_runtime = "python3.9"
        function_arn = (
            f"arn:aws:lambda:{AWS_REGION}:{DEFAULT_ACCOUNT_ID}:function/{function_name}"
        )
        lambda_client.functions = {
            "function_name": Function(
                name=function_name,
                arn=function_arn,
                region=AWS_REGION,
                runtime=function_runtime,
            )
        }

        with mock.patch(
            "prowler.providers.aws.services.awslambda.awslambda_service.Lambda",
            new=lambda_client,
        ), mock.patch(
            "prowler.providers.aws.services.awslambda.awslambda_function_using_supported_runtimes.awslambda_function_using_supported_runtimes.get_config_var",
            new=mock_get_config_var,
        ):
            # Test Check
            from prowler.providers.aws.services.awslambda.awslambda_function_using_supported_runtimes.awslambda_function_using_supported_runtimes import (
                awslambda_function_using_supported_runtimes,
            )

            check = awslambda_function_using_supported_runtimes()
            result = check.execute()

            assert len(result) == 1
            assert result[0].region == AWS_REGION
            assert result[0].resource_id == function_name
            assert result[0].resource_arn == function_arn
            assert result[0].status == "PASS"
            assert (
                result[0].status_extended
                == f"Lambda function {function_name} is using {function_runtime} which is supported"
            )

    def test_function_no_runtime(self):
        lambda_client = mock.MagicMock
        function_name = "test-lambda"
        function_arn = (
            f"arn:aws:lambda:{AWS_REGION}:{DEFAULT_ACCOUNT_ID}:function/{function_name}"
        )
        lambda_client.functions = {
            "function_name": Function(
                name=function_name, arn=function_arn, region=AWS_REGION
            )
        }

        with mock.patch(
            "prowler.providers.aws.services.awslambda.awslambda_service.Lambda",
            new=lambda_client,
        ), mock.patch(
            "prowler.providers.aws.services.awslambda.awslambda_function_using_supported_runtimes.awslambda_function_using_supported_runtimes.get_config_var",
            new=mock_get_config_var,
        ):
            # Test Check
            from prowler.providers.aws.services.awslambda.awslambda_function_using_supported_runtimes.awslambda_function_using_supported_runtimes import (
                awslambda_function_using_supported_runtimes,
            )

            check = awslambda_function_using_supported_runtimes()
            result = check.execute()

            assert len(result) == 0
