from datetime import datetime, timezone
from os import getcwd

timestamp = datetime.today()
timestamp_utc = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
prowler_version = "3.0-alpha"

# Groups
groups_file = "groups.json"

# AWS services-regions matrix json
aws_services_json_file = "providers/aws/aws_regions_by_service.json"

default_output_directory = getcwd() + "/output"

output_file_timestamp = timestamp.strftime("%Y%m%d%H%M%S")
csv_file_suffix = f"{output_file_timestamp}.csv"
json_file_suffix = f"{output_file_timestamp}.json"
json_asff_file_suffix = f"{output_file_timestamp}.asff.json"