import threading

from pydantic import BaseModel

from prowler.lib.logger import logger
from prowler.providers.aws.aws_provider import generate_regional_clients


################## AccessAnalyzer
class AccessAnalyzer:
    def __init__(self, audit_info):
        self.service = "accessanalyzer"
        self.session = audit_info.audit_session
        self.audited_account = audit_info.audited_account
        self.regional_clients = generate_regional_clients(self.service, audit_info)
        self.analyzers = []
        self.__threading_call__(self.__list_analyzers__)
        self.__list_findings__()
        self.__get_finding_status__()

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

    def __list_analyzers__(self, regional_client):
        logger.info("AccessAnalyzer - Listing Analyzers...")
        try:
            list_analyzers_paginator = regional_client.get_paginator("list_analyzers")
            analyzer_count = 0
            for page in list_analyzers_paginator.paginate():
                analyzer_count += len(page["analyzers"])
                for analyzer in page["analyzers"]:
                    self.analyzers.append(
                        Analyzer(
                            arn=analyzer["arn"],
                            name=analyzer["name"],
                            status=analyzer["status"],
                            tags=str(analyzer["tags"]),
                            type=analyzer["type"],
                            region=regional_client.region,
                        )
                    )
            # No analyzers in region
            if analyzer_count == 0:
                self.analyzers.append(
                    Analyzer(
                        arn="",
                        name=self.audited_account,
                        status="NOT_AVAILABLE",
                        tags="",
                        type="",
                        region=regional_client.region,
                    )
                )

        except Exception as error:
            logger.error(
                f"{regional_client.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )

    def __get_finding_status__(self):
        logger.info("AccessAnalyzer - Get Finding status...")
        try:
            for analyzer in self.analyzers:
                if analyzer.status != "NOT_AVAILABLE":
                    regional_client = self.regional_clients[analyzer.region]
                    for finding in analyzer.findings:
                        finding_information = regional_client.get_finding(
                            analyzerArn=analyzer.arn, id=finding.id
                        )
                        finding.status = finding_information["finding"]["status"]

        except Exception as error:
            logger.error(
                f"{regional_client.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )

    def __list_findings__(self):
        logger.info("AccessAnalyzer - Listing Findings per Analyzer...")
        try:
            for analyzer in self.analyzers:
                if analyzer.status != "NOT_AVAILABLE":
                    regional_client = self.regional_clients[analyzer.region]
                    list_findings_paginator = regional_client.get_paginator(
                        "list_findings"
                    )
                    for page in list_findings_paginator.paginate(
                        analyzerArn=analyzer.arn
                    ):
                        for finding in page["findings"]:
                            analyzer.findings.append(Finding(id=finding["id"]))

        except Exception as error:
            logger.error(
                f"{regional_client.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )


class Finding(BaseModel):
    id: str
    status: str = ""


class Analyzer(BaseModel):
    arn: str
    name: str
    status: str
    findings: list[Finding] = []
    tags: str
    type: str
    region: str
