#!/usr/bin/env python3

"""
(c) Deductive 2020, all rights reserved
"""

import logging
import sys
import json

"""
Initialise logger and stdout stream
"""
logger = logging.getLogger(__name__)
stdout = logging.StreamHandler(sys.stdout)
stdout.setFormatter(logging.Formatter('%(message)s'))
stdout.setLevel(logging.INFO)
logger.addHandler(stdout)
logger.setLevel(logging.INFO)

""" Example output file
{
    "production": {
        "django_settings": "core.settings",
        "profile_name": "inscape",
        "project_name": "reporting",
        "runtime": "python3.6",
        "s3_bucket": "reporting-production",
        "environment_variables": {
            "STATIC_S3_BUCKET": "reporting-production"
        }
    }
}
"""

if __name__ == "__main__":

    """
    Check arguments
    """
    if len(sys.argv) != 20:

        logger.info("Cannot create Zappa settings file. Incorrect arguments: " +
                    str(sys.argv))

    else:

        """
        Get arguments
        """
        path = str(sys.argv[1])  # e.g. './django/zappa_settings.json'
        project = str(sys.argv[2])  # e.g. 'reporting-tool'
        aws_stage = str(sys.argv[3])  # e.g. 'DEV-CLIVE'
        zappa_stage = str(sys.argv[4])  # e.g. 'dev_clive'
        profile = str(sys.argv[5])  # AWS profile e.g. 'inscape'
        region = str(sys.argv[6])  # e.g. 'us-east-1'
        dbname = str(sys.argv[7])
        dbuser = str(sys.argv[8])
        dbpword = str(sys.argv[9])
        dbhost = str(sys.argv[10])
        dbport = str(sys.argv[11])
        subnetids = str(sys.argv[12])
        securitygroupids = str(sys.argv[13])
        supass = str(sys.argv[14])
        domain = str(sys.argv[15])
        subdomain = str(sys.argv[16])
        staticsub = str(sys.argv[17])
        sslcert = str(sys.argv[18])
        secretkey = str(sys.argv[19])

        bucket = "{}-{}".format(project, aws_stage.lower())
        domain_url = "{}.{}".format(subdomain, domain)
        static_url = "{}.{}".format(staticsub, domain)

        """
        Generate the Zappa settings
        https://github.com/Miserlou/Zappa#advanced-settings
        """
        zappa_settings = {}

        stage_settings = {
            'django_settings': 'deductive.settings',
            'profile_name': profile,
            'project_name': "{}-{}".format(project, 'zappa'),
            'runtime': 'python3.6',
            's3_bucket': bucket,
            'aws_region': region,
            'memory_size': 3008,
            'environment_variables': {
                'STATIC_S3_BUCKET': bucket,
                'AURORA_DB_NAME': dbname,
                'AURORA_DB_USER': dbuser,
                'AURORA_DB_PWORD': dbpword,
                'AURORA_DB_HOST': dbhost,
                'AURORA_DB_PORT': dbport,
                'SU_NAME': 'admin',
                'SU_EMAIL': '',
                'SU_PASS': supass,
                'CUSTOM_DOMAIN': domain_url,
                'STATIC_CUSTOM_DOMAIN': static_url,
                'SECRET_KEY': secretkey,
                'AWS_STAGE': aws_stage
            },
            'vpc_config': {
                'SubnetIds': subnetids.split(','),
                'SecurityGroupIds': securitygroupids.split(',')
            },
            'certificate_arn': sslcert,
            'domain': domain_url,
            'cors': True,
            'include': ["libmysqlclient.so.18"],
            'exclude': [
                "_pycache_",
                "*.pyc",
                "tests",
                "examples",
                "static",
                "boto3",
                "botocore"
            ],
            'delete_local_zip': True,
            'slim_handler': True,
            'timeout_seconds': 60,
            'cache_cluster_enabled': True,
            'cache_cluster_ttl': 3600,
            'cache_cluster_size': 1.6,
            'keep_warm_expression': 'rate(4 minutes)',
            'keep_warm': True,
        }

        zappa_settings[zappa_stage] = stage_settings

        """
        Save the Zappa settings
        """
        with open(path, 'w') as outfile:
            outfile.write(json.dumps(zappa_settings, indent=4))
