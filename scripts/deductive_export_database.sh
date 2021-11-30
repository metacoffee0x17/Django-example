#!/bin/bash -xe

# (c) Deductive 2020, all rights reserved
#
# Exports database from RDS cluster and uploads to S3.
# Expects certain environment variables to be set up by EC2 UserData
# Designed to be run on bastion server via SSM AWS-RunRemoteScript command

# Load the variables from config file
source "/home/ssm-user/deductivewebsite-envars.sh"

TIMESTAMP=`date "+%Y-%m-%d"`
DB_DUMP_PATH="${WORKING_DIR}/${TIMESTAMP}-${DB_NAME}-${DEPLOY_STAGE}.sql"

# Get actual db password from SecretsManager
PASSWORD=$(aws secretsmanager get-secret-value --secret-id $DB_SECRET  --output text --query '[SecretString]' --region=$AWS_REGION 2>/dev/null)

# Dump the database locally
mysqldump -h $DB_HOST -u $DB_USER -p$PASSWORD --databases $DB_NAME --single-transaction --order-by-primary -r $DB_DUMP_PATH

# Upload database dump to S3
aws s3 cp $DB_DUMP_PATH "s3://${DEST_BUCKET}/${DEST_PREFIX}/"