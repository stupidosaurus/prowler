from datetime import datetime, timedelta, timezone
from re import search
from unittest import mock

from boto3 import client
from moto import mock_cloudtrail, mock_s3


class Test_cloudtrail_cloudwatch_logging_enabled:
    @mock_cloudtrail
    @mock_s3
    def test_trails_sending_logs_during_and_not_last_day(self):
        cloudtrail_client_us_east_1 = client("cloudtrail", region_name="us-east-1")
        s3_client_us_east_1 = client("s3", region_name="us-east-1")
        cloudtrail_client_eu_west_1 = client("cloudtrail", region_name="eu-west-1")
        s3_client_eu_west_1 = client("s3", region_name="eu-west-1")
        trail_name_us = "trail_test_us"
        bucket_name_us = "bucket_test_us"
        trail_name_eu = "trail_test_eu"
        bucket_name_eu = "bucket_test_eu"
        s3_client_us_east_1.create_bucket(Bucket=bucket_name_us)
        s3_client_eu_west_1.create_bucket(
            Bucket=bucket_name_eu,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )
        trail_us = cloudtrail_client_us_east_1.create_trail(
            Name=trail_name_us, S3BucketName=bucket_name_us, IsMultiRegionTrail=False
        )
        trail_eu = cloudtrail_client_eu_west_1.create_trail(
            Name=trail_name_eu, S3BucketName=bucket_name_eu, IsMultiRegionTrail=False
        )

        from prowler.providers.aws.lib.audit_info.audit_info import current_audit_info
        from prowler.providers.aws.services.cloudtrail.cloudtrail_service import (
            Cloudtrail,
        )

        current_audit_info.audited_partition = "aws"
        current_audit_info.audited_regions = ["eu-west-1", "us-east-1"]

        with mock.patch(
            "prowler.providers.aws.services.cloudtrail.cloudtrail_cloudwatch_logging_enabled.cloudtrail_cloudwatch_logging_enabled.cloudtrail_client",
            new=Cloudtrail(current_audit_info),
        ) as service_client:
            # Test Check
            from prowler.providers.aws.services.cloudtrail.cloudtrail_cloudwatch_logging_enabled.cloudtrail_cloudwatch_logging_enabled import (
                cloudtrail_cloudwatch_logging_enabled,
            )

            for trail in service_client.trails:
                if trail.name == trail_name_us:
                    trail.latest_cloudwatch_delivery_time = datetime.now().replace(
                        tzinfo=timezone.utc
                    )
                elif trail.name == trail_name_eu:
                    trail.latest_cloudwatch_delivery_time = (
                        datetime.now() - timedelta(days=2)
                    ).replace(tzinfo=timezone.utc)

            regions = []
            for region in service_client.regional_clients.keys():
                regions.append(region)

            check = cloudtrail_cloudwatch_logging_enabled()
            result = check.execute()
            # len of result if has to be 2 since we only have 2 single region trails
            assert len(result) == 2
            for report in result:
                if report.resource_id == trail_name_us:
                    assert report.resource_id == trail_name_us
                    assert report.resource_arn == trail_us["TrailARN"]
                    assert report.status == "PASS"
                    assert search(
                        report.status_extended,
                        f"Single region trail {trail_name_us} has been logging the last 24h",
                    )
                if report.resource_id == trail_name_eu:
                    assert report.resource_id == trail_name_eu
                    assert report.resource_arn == trail_eu["TrailARN"]
                    assert report.status == "FAIL"
                    assert search(
                        report.status_extended,
                        f"Single region trail {trail_name_eu} is not logging in the last 24h",
                    )

    @mock_cloudtrail
    @mock_s3
    def test_multi_region_and_single_region_logging_and_not(self):
        cloudtrail_client_us_east_1 = client("cloudtrail", region_name="us-east-1")
        s3_client_us_east_1 = client("s3", region_name="us-east-1")
        cloudtrail_client_eu_west_1 = client("cloudtrail", region_name="eu-west-1")
        s3_client_eu_west_1 = client("s3", region_name="eu-west-1")
        trail_name_us = "trail_test_us"
        bucket_name_us = "bucket_test_us"
        trail_name_eu = "trail_test_eu"
        bucket_name_eu = "bucket_test_eu"
        s3_client_us_east_1.create_bucket(Bucket=bucket_name_us)
        s3_client_eu_west_1.create_bucket(
            Bucket=bucket_name_eu,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )
        trail_us = cloudtrail_client_us_east_1.create_trail(
            Name=trail_name_us, S3BucketName=bucket_name_us, IsMultiRegionTrail=True
        )
        trail_eu = cloudtrail_client_eu_west_1.create_trail(
            Name=trail_name_eu, S3BucketName=bucket_name_eu, IsMultiRegionTrail=False
        )

        from prowler.providers.aws.lib.audit_info.audit_info import current_audit_info
        from prowler.providers.aws.services.cloudtrail.cloudtrail_service import (
            Cloudtrail,
        )

        current_audit_info.audited_partition = "aws"
        current_audit_info.audited_regions = ["eu-west-1", "us-east-1"]

        with mock.patch(
            "prowler.providers.aws.services.cloudtrail.cloudtrail_cloudwatch_logging_enabled.cloudtrail_cloudwatch_logging_enabled.cloudtrail_client",
            new=Cloudtrail(current_audit_info),
        ) as service_client:
            # Test Check
            from prowler.providers.aws.services.cloudtrail.cloudtrail_cloudwatch_logging_enabled.cloudtrail_cloudwatch_logging_enabled import (
                cloudtrail_cloudwatch_logging_enabled,
            )

            for trail in service_client.trails:
                if trail.name == trail_name_us:
                    trail.latest_cloudwatch_delivery_time = datetime.now().replace(
                        tzinfo=timezone.utc
                    )
                elif trail.name == trail_name_eu:
                    trail.latest_cloudwatch_delivery_time = (
                        datetime.now() - timedelta(days=2)
                    ).replace(tzinfo=timezone.utc)

            regions = []
            for region in service_client.regional_clients.keys():
                regions.append(region)

            check = cloudtrail_cloudwatch_logging_enabled()
            result = check.execute()
            # len of result should be 3 -> (1 multiregion entry per region + 1 entry because of single region trail)
            assert len(result) == 3
            for report in result:
                if report.resource_id == trail_name_us:
                    assert report.resource_id == trail_name_us
                    assert report.resource_arn == trail_us["TrailARN"]
                    assert report.status == "PASS"
                    assert search(
                        report.status_extended,
                        f"Multiregion trail {trail_name_us} has been logging the last 24h",
                    )
                if report.resource_id == trail_name_eu and report.region == "eu-west-1":
                    assert report.resource_id == trail_name_eu
                    assert report.resource_arn == trail_eu["TrailARN"]
                    assert report.status == "FAIL"
                    assert search(
                        report.status_extended,
                        f"Single region trail {trail_name_eu} is not logging in the last 24h",
                    )

    @mock_cloudtrail
    @mock_s3
    def test_trails_sending_and_not_sending_logs(self):
        cloudtrail_client_us_east_1 = client("cloudtrail", region_name="us-east-1")
        s3_client_us_east_1 = client("s3", region_name="us-east-1")
        cloudtrail_client_eu_west_1 = client("cloudtrail", region_name="eu-west-1")
        s3_client_eu_west_1 = client("s3", region_name="eu-west-1")
        trail_name_us = "trail_test_us"
        bucket_name_us = "bucket_test_us"
        trail_name_eu = "trail_test_eu"
        bucket_name_eu = "bucket_test_eu"
        s3_client_us_east_1.create_bucket(Bucket=bucket_name_us)
        s3_client_eu_west_1.create_bucket(
            Bucket=bucket_name_eu,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )
        trail_us = cloudtrail_client_us_east_1.create_trail(
            Name=trail_name_us, S3BucketName=bucket_name_us, IsMultiRegionTrail=False
        )
        trail_eu = cloudtrail_client_eu_west_1.create_trail(
            Name=trail_name_eu, S3BucketName=bucket_name_eu, IsMultiRegionTrail=False
        )

        from prowler.providers.aws.lib.audit_info.audit_info import current_audit_info
        from prowler.providers.aws.services.cloudtrail.cloudtrail_service import (
            Cloudtrail,
        )

        current_audit_info.audited_partition = "aws"
        current_audit_info.audited_regions = ["eu-west-1", "us-east-1"]

        with mock.patch(
            "prowler.providers.aws.services.cloudtrail.cloudtrail_cloudwatch_logging_enabled.cloudtrail_cloudwatch_logging_enabled.cloudtrail_client",
            new=Cloudtrail(current_audit_info),
        ) as service_client:
            # Test Check
            from prowler.providers.aws.services.cloudtrail.cloudtrail_cloudwatch_logging_enabled.cloudtrail_cloudwatch_logging_enabled import (
                cloudtrail_cloudwatch_logging_enabled,
            )

            for trail in service_client.trails:
                if trail.name == trail_name_us:
                    trail.latest_cloudwatch_delivery_time = datetime.now().replace(
                        tzinfo=timezone.utc
                    )
                elif trail.name == trail_name_us:
                    trail.latest_cloudwatch_delivery_time = None

            regions = []
            for region in service_client.regional_clients.keys():
                regions.append(region)

            check = cloudtrail_cloudwatch_logging_enabled()
            result = check.execute()
            # len of result if has to be 2 since we only have 2 single region trails
            assert len(result) == 2
            for report in result:
                if report.resource_id == trail_name_us:
                    assert report.resource_id == trail_name_us
                    assert report.resource_arn == trail_us["TrailARN"]
                    assert report.status == "PASS"
                    assert (
                        report.status_extended
                        == f"Single region trail {trail_name_us} has been logging the last 24h"
                    )
                if report.resource_id == trail_name_eu:
                    assert report.resource_id == trail_name_eu
                    assert report.resource_arn == trail_eu["TrailARN"]
                    assert report.status == "FAIL"
                    assert (
                        report.status_extended
                        == f"Single region trail {trail_name_eu} is not logging in the last 24h or not configured to deliver logs"
                    )
