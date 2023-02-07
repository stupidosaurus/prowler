import threading
from datetime import datetime

from pydantic import BaseModel

from prowler.lib.logger import logger
from prowler.providers.aws.aws_provider import generate_regional_clients


################### CLOUDTRAIL
class Cloudtrail:
    def __init__(self, audit_info):
        self.service = "cloudtrail"
        self.session = audit_info.audit_session
        self.audited_account = audit_info.audited_account
        self.audited_partition = audit_info.audited_partition
        self.region = audit_info.profile_region
        self.regional_clients = generate_regional_clients(self.service, audit_info)
        self.trails = []
        self.__threading_call__(self.__get_trails__)
        self.__get_trail_status__()
        self.__get_event_selectors__()

    def __get_session__(self):
        return self.session

    def __threading_call__(self, call):
        threads = []
        for regional_client in self.regional_clients.values():
            threads.append(threading.Thread(target=call, args=(regional_client,)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def __get_trails__(self, regional_client):
        logger.info("Cloudtrail - Getting trails...")
        try:
            describe_trails = regional_client.describe_trails()["trailList"]
            if describe_trails:
                for trail in describe_trails:
                    kms_key_id = None
                    log_group_arn = None
                    if "KmsKeyId" in trail:
                        kms_key_id = trail["KmsKeyId"]
                    if "CloudWatchLogsLogGroupArn" in trail:
                        log_group_arn = trail["CloudWatchLogsLogGroupArn"]
                    self.trails.append(
                        Trail(
                            name=trail["Name"],
                            is_multiregion=trail["IsMultiRegionTrail"],
                            home_region=trail["HomeRegion"],
                            arn=trail["TrailARN"],
                            region=regional_client.region,
                            is_logging=False,
                            log_file_validation_enabled=trail[
                                "LogFileValidationEnabled"
                            ],
                            latest_cloudwatch_delivery_time=None,
                            s3_bucket=trail["S3BucketName"],
                            kms_key=kms_key_id,
                            log_group_arn=log_group_arn,
                            data_events=[],
                        )
                    )
            else:
                self.trails.append(
                    Trail(
                        region=regional_client.region,
                    )
                )

        except Exception as error:
            logger.error(
                f"{regional_client.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )

    def __get_trail_status__(self):
        logger.info("Cloudtrail - Getting trail status")
        try:
            for trail in self.trails:
                for region, client in self.regional_clients.items():
                    if trail.region == region and trail.name:
                        status = client.get_trail_status(Name=trail.arn)
                        trail.is_logging = status["IsLogging"]
                        if "LatestCloudWatchLogsDeliveryTime" in status:
                            trail.latest_cloudwatch_delivery_time = status[
                                "LatestCloudWatchLogsDeliveryTime"
                            ]

        except Exception as error:
            logger.error(
                f"{client.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )

    def __get_event_selectors__(self):
        logger.info("Cloudtrail - Getting event selector")
        try:
            for trail in self.trails:
                for region, client in self.regional_clients.items():
                    if trail.region == region and trail.name:
                        data_events = client.get_event_selectors(TrailName=trail.arn)
                        # check if key exists and array associated to that key is not empty
                        if (
                            "EventSelectors" in data_events
                            and data_events["EventSelectors"]
                        ):
                            for event in data_events["EventSelectors"]:
                                event_selector = Event_Selector(
                                    is_advanced=False, event_selector=event
                                )
                                trail.data_events.append(event_selector)
                        # check if key exists and array associated to that key is not empty
                        elif (
                            "AdvancedEventSelectors" in data_events
                            and data_events["AdvancedEventSelectors"]
                        ):
                            for event in data_events["AdvancedEventSelectors"]:
                                event_selector = Event_Selector(
                                    is_advanced=True, event_selector=event
                                )
                                trail.data_events.append(event_selector)

        except Exception as error:
            logger.error(
                f"{client.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )


class Event_Selector(BaseModel):
    is_advanced: bool
    event_selector: dict


class Trail(BaseModel):
    name: str = None
    is_multiregion: bool = None
    home_region: str = None
    arn: str = None
    region: str
    is_logging: bool = None
    log_file_validation_enabled: bool = None
    latest_cloudwatch_delivery_time: datetime = None
    s3_bucket: str = None
    kms_key: str = None
    log_group_arn: str = None
    data_events: list[Event_Selector] = []
