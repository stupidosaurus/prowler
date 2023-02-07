from prowler.lib.check.models import Check, Check_Report_AWS
from prowler.providers.aws.services.cloudtrail.cloudtrail_client import (
    cloudtrail_client,
)


class cloudtrail_s3_dataevents_read_enabled(Check):
    def execute(self):
        findings = []
        report = Check_Report_AWS(self.metadata())
        report.region = cloudtrail_client.region
        report.resource_id = "No trails"
        report.resource_arn = "No trails"
        report.status = "FAIL"
        report.status_extended = "No CloudTrail trails have a data event to record all S3 object-level API operations."
        for trail in cloudtrail_client.trails:
            for data_event in trail.data_events:
                # classic event selectors
                if not data_event.is_advanced:
                    # Check if trail has a data event for all S3 Buckets for read
                    if (
                        data_event.event_selector["ReadWriteType"] == "ReadOnly"
                        or data_event.event_selector["ReadWriteType"] == "All"
                    ):
                        for resource in data_event.event_selector["DataResources"]:
                            if "AWS::S3::Object" == resource["Type"] and (
                                f"arn:{cloudtrail_client.audited_partition}:s3"
                                in resource["Values"]
                                or f"arn:{cloudtrail_client.audited_partition}:s3:::*/*"
                                in resource["Values"]
                            ):
                                report.region = trail.region
                                report.resource_id = trail.name
                                report.resource_arn = trail.arn
                                report.status = "PASS"
                                report.status_extended = f"Trail {trail.name} has a classic data event selector to record all S3 object-level API operations."
                # advanced event selectors
                elif data_event.is_advanced:
                    for field_selector in data_event.event_selector["FieldSelectors"]:
                        if (
                            field_selector["Field"] == "resources.type"
                            and field_selector["Equals"][0] == "AWS::S3::Object"
                        ):
                            report.region = trail.region
                            report.resource_id = trail.name
                            report.resource_arn = trail.arn
                            report.status = "PASS"
                            report.status_extended = f"Trail {trail.name} has an advanced data event selector to record all S3 object-level API operations."

        findings.append(report)
        return findings
