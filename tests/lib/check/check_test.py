import os
import pathlib
from importlib.machinery import FileFinder
from pkgutil import ModuleInfo

from mock import patch

from prowler.lib.check.check import (
    exclude_checks_to_run,
    exclude_services_to_run,
    list_modules,
    list_services,
    parse_checks_from_file,
    recover_checks_from_provider,
    update_audit_metadata,
)
from prowler.lib.check.models import load_check_metadata

expected_packages = [
    ModuleInfo(
        module_finder=FileFinder(
            "/root_dir/prowler/providers/azure/services/storage/storage_ensure_minimum_tls_version_12"
        ),
        name="prowler.providers.azure.services.storage.storage_ensure_minimum_tls_version_12.storage_ensure_minimum_tls_version_12",
        ispkg=False,
    ),
    ModuleInfo(
        module_finder=FileFinder("/root_dir/prowler/providers/azure/services/storage"),
        name="prowler.providers.azure.services.storage.storage_ensure_encryption_with_customer_managed_keys",
        ispkg=True,
    ),
    ModuleInfo(
        module_finder=FileFinder(
            "/root_dir/prowler/providers/azure/services/storage/storage_ensure_encryption_with_customer_managed_keys"
        ),
        name="prowler.providers.azure.services.storage.storage_ensure_encryption_with_customer_managed_keys.storage_ensure_encryption_with_customer_managed_keys",
        ispkg=False,
    ),
]


def mock_walk_packages(*_):
    return expected_packages


def mock_list_modules(*_):
    modules = [
        ModuleInfo(
            module_finder=FileFinder(
                "/root_dir/prowler/providers/azure/services/storage/storage_ensure_minimum_tls_version_12"
            ),
            name="prowler.providers.azure.services.storage.storage_ensure_minimum_tls_version_12.storage_ensure_minimum_tls_version_12",
            ispkg=False,
        ),
        ModuleInfo(
            module_finder=FileFinder(
                "/root_dir/prowler/providers/azure/services/storage"
            ),
            name="prowler.providers.azure.services.storage.storage_ensure_encryption_with_customer_managed_keys",
            ispkg=True,
        ),
        ModuleInfo(
            module_finder=FileFinder(
                "/root_dir/prowler/providers/azure/services/storage/storage_ensure_encryption_with_customer_managed_keys"
            ),
            name="prowler.providers.azure.services.storage.storage_ensure_encryption_with_customer_managed_keys.storage_ensure_encryption_with_customer_managed_keys",
            ispkg=False,
        ),
    ]
    return modules


def mock_recover_checks_from_azure_provider(*_):
    return [
        (
            "defender_ensure_defender_for_app_services_is_on",
            "/root_dir/fake_path/defender/defender_ensure_defender_for_app_services_is_on",
        ),
        (
            "iam_subscription_roles_owner_custom_not_created",
            "/root_dir/fake_path/iam/iam_subscription_roles_owner_custom_not_created",
        ),
        (
            "storage_default_network_access_rule_is_denied",
            "/root_dir/fake_path/storage/storage_default_network_access_rule_is_denied",
        ),
    ]


def mock_recover_checks_from_aws_provider(*_):
    return [
        (
            "accessanalyzer_enabled_without_findings",
            "/root_dir/fake_path/accessanalyzer/accessanalyzer_enabled_without_findings",
        ),
        (
            "awslambda_function_url_cors_policy",
            "/root_dir/fake_path/awslambda/awslambda_function_url_cors_policy",
        ),
        (
            "ec2_securitygroup_allow_ingress_from_internet_to_any_port",
            "/root_dir/fake_path/ec2/ec2_securitygroup_allow_ingress_from_internet_to_any_port",
        ),
    ]


class Test_Check:
    def test_load_check_metadata(self):
        test_cases = [
            {
                "input": {
                    "metadata_path": f"{os.path.dirname(os.path.realpath(__file__))}/fixtures/metadata.json",
                },
                "expected": {
                    "CheckID": "iam_disable_30_days_credentials",
                    "CheckTitle": "Ensure credentials unused for 30 days or greater are disabled",
                    "ServiceName": "iam",
                    "Severity": "low",
                },
            }
        ]
        for test in test_cases:
            metadata_path = test["input"]["metadata_path"]
            check_metadata = load_check_metadata(metadata_path)
            assert check_metadata.CheckID == test["expected"]["CheckID"]
            assert check_metadata.CheckTitle == test["expected"]["CheckTitle"]
            assert check_metadata.ServiceName == test["expected"]["ServiceName"]
            assert check_metadata.Severity == test["expected"]["Severity"]

    def test_parse_checks_from_file(self):
        test_cases = [
            {
                "input": {
                    "path": f"{pathlib.Path().absolute()}/tests/lib/check/fixtures/checklistA.json",
                    "provider": "aws",
                },
                "expected": {"check11", "check12", "check7777"},
            }
        ]
        for test in test_cases:
            check_file = test["input"]["path"]
            provider = test["input"]["provider"]
            assert parse_checks_from_file(check_file, provider) == test["expected"]

    def test_exclude_checks_to_run(self):
        test_cases = [
            {
                "input": {
                    "check_list": {"check12", "check11", "extra72", "check13"},
                    "excluded_checks": {"check12", "check13"},
                },
                "expected": {"check11", "extra72"},
            },
            {
                "input": {
                    "check_list": {"check112", "check11", "extra72", "check13"},
                    "excluded_checks": {"check12", "check13", "check14"},
                },
                "expected": {"check112", "check11", "extra72"},
            },
        ]
        for test in test_cases:
            check_list = test["input"]["check_list"]
            excluded_checks = test["input"]["excluded_checks"]
            assert (
                exclude_checks_to_run(check_list, excluded_checks) == test["expected"]
            )

    def test_exclude_services_to_run(self):
        test_cases = [
            {
                "input": {
                    "checks_to_run": {
                        "iam_disable_30_days_credentials",
                        "iam_disable_90_days_credentials",
                    },
                    "excluded_services": {"ec2"},
                    "provider": "aws",
                },
                "expected": {
                    "iam_disable_30_days_credentials",
                    "iam_disable_90_days_credentials",
                },
            },
            {
                "input": {
                    "checks_to_run": {
                        "iam_disable_30_days_credentials",
                        "iam_disable_90_days_credentials",
                    },
                    "excluded_services": {"iam"},
                    "provider": "aws",
                },
                "expected": set(),
            },
        ]
        for test in test_cases:
            excluded_services = test["input"]["excluded_services"]
            checks_to_run = test["input"]["checks_to_run"]
            provider = test["input"]["provider"]
            assert (
                exclude_services_to_run(checks_to_run, excluded_services, provider)
                == test["expected"]
            )

    @patch(
        "prowler.lib.check.check.recover_checks_from_provider",
        new=mock_recover_checks_from_azure_provider,
    )
    def test_list_azure_services(self):
        provider = "azure"
        expected_services = {"defender", "iam", "storage"}
        listed_services = list_services(provider)
        assert listed_services == sorted(expected_services)

    @patch(
        "prowler.lib.check.check.recover_checks_from_provider",
        new=mock_recover_checks_from_aws_provider,
    )
    def test_list_aws_services(self):
        provider = "azure"
        expected_services = {"accessanalyzer", "awslambda", "ec2"}
        listed_services = list_services(provider)
        assert listed_services == sorted(expected_services)

    @patch("prowler.lib.check.check.list_modules", new=mock_list_modules)
    def test_recover_checks_from_provider(self):
        provider = "azure"
        service = "storage"
        expected_checks = [
            (
                "storage_ensure_minimum_tls_version_12",
                "/root_dir/prowler/providers/azure/services/storage/storage_ensure_minimum_tls_version_12",
            ),
            (
                "storage_ensure_encryption_with_customer_managed_keys",
                "/root_dir/prowler/providers/azure/services/storage/storage_ensure_encryption_with_customer_managed_keys",
            ),
        ]
        returned_checks = recover_checks_from_provider(provider, service)
        assert returned_checks == expected_checks

    @patch("prowler.lib.check.check.walk_packages", new=mock_walk_packages)
    def test_list_modules(self):
        provider = "azure"
        service = "storage"
        expected_modules = list_modules(provider, service)
        assert expected_modules == expected_packages

    # def test_parse_checks_from_compliance_framework_two(self):
    #     test_case = {
    #         "input": {"compliance_frameworks": ["cis_v1.4_aws", "ens_v3_aws"]},
    #         "expected": {
    #             "vpc_flow_logs_enabled",
    #             "ec2_ebs_snapshot_encryption",
    #             "iam_user_mfa_enabled_console_access",
    #             "cloudtrail_multi_region_enabled",
    #             "ec2_elbv2_insecure_ssl_ciphers",
    #             "guardduty_is_enabled",
    #             "s3_bucket_default_encryption",
    #             "cloudfront_distributions_https_enabled",
    #             "iam_avoid_root_usage",
    #             "s3_bucket_secure_transport_policy",
    #         },
    #     }
    #     with mock.patch(
    #         "prowler.lib.check.check.compliance_specification_dir_path",
    #         new=f"{pathlib.Path().absolute()}/fixtures",
    #     ):
    #         provider = "aws"
    #         bulk_compliance_frameworks = bulk_load_compliance_frameworks(provider)
    #         compliance_frameworks = test_case["input"]["compliance_frameworks"]
    #         assert (
    #             parse_checks_from_compliance_framework(
    #                 compliance_frameworks, bulk_compliance_frameworks
    #             )
    #             == test_case["expected"]
    #         )

    # def test_parse_checks_from_compliance_framework_one(self):
    #     test_case = {
    #         "input": {"compliance_frameworks": ["cis_v1.4_aws"]},
    #         "expected": {
    #             "iam_user_mfa_enabled_console_access",
    #             "s3_bucket_default_encryption",
    #             "iam_avoid_root_usage",
    #         },
    #     }
    #     with mock.patch(
    #         "prowler.lib.check.check.compliance_specification_dir",
    #         new=f"{pathlib.Path().absolute()}/fixtures",
    #     ):
    #         provider = "aws"
    #         bulk_compliance_frameworks = bulk_load_compliance_frameworks(provider)
    #         compliance_frameworks = test_case["input"]["compliance_frameworks"]
    #         assert (
    #             parse_checks_from_compliance_framework(
    #                 compliance_frameworks, bulk_compliance_frameworks
    #             )
    #             == test_case["expected"]
    #         )

    # def test_parse_checks_from_compliance_framework_no_compliance(self):
    #     test_case = {
    #         "input": {"compliance_frameworks": []},
    #         "expected": set(),
    #     }
    #     with mock.patch(
    #         "prowler.lib.check.check.compliance_specification_dir",
    #         new=f"{pathlib.Path().absolute()}/fixtures",
    #     ):
    #         provider = "aws"
    #         bulk_compliance_frameworks = bulk_load_compliance_frameworks(provider)
    #         compliance_frameworks = test_case["input"]["compliance_frameworks"]
    #         assert (
    #             parse_checks_from_compliance_framework(
    #                 compliance_frameworks, bulk_compliance_frameworks
    #             )
    #             == test_case["expected"]
    #         )

    def test_update_audit_metadata_complete(self):
        from prowler.providers.common.models import Audit_Metadata

        # Set the expected checks to run
        expected_checks = ["iam_administrator_access_with_mfa"]
        services_executed = {"iam"}
        checks_executed = {"iam_administrator_access_with_mfa"}

        # Set an empty Audit_Metadata
        audit_metadata = Audit_Metadata(
            services_scanned=0,
            expected_checks=expected_checks,
            completed_checks=0,
            audit_progress=0,
        )

        audit_metadata = update_audit_metadata(
            audit_metadata, services_executed, checks_executed
        )

        assert audit_metadata.audit_progress == float(100)
        assert audit_metadata.services_scanned == 1
        assert audit_metadata.expected_checks == expected_checks
        assert audit_metadata.completed_checks == 1

    def test_update_audit_metadata_50(self):
        from prowler.providers.common.models import Audit_Metadata

        # Set the expected checks to run
        expected_checks = [
            "iam_administrator_access_with_mfa",
            "iam_support_role_created",
        ]
        services_executed = {"iam"}
        checks_executed = {"iam_administrator_access_with_mfa"}

        # Set an empty Audit_Metadata
        audit_metadata = Audit_Metadata(
            services_scanned=0,
            expected_checks=expected_checks,
            completed_checks=0,
            audit_progress=0,
        )

        audit_metadata = update_audit_metadata(
            audit_metadata, services_executed, checks_executed
        )

        assert audit_metadata.audit_progress == float(50)
        assert audit_metadata.services_scanned == 1
        assert audit_metadata.expected_checks == expected_checks
        assert audit_metadata.completed_checks == 1
