#!/bin/bash -xe

# (c) Deductive 2020, all rights reserved
#
# Exports database from RDS cluster and uploads to S3.
# Expects certain environment variables to be set up by EC2 UserData
# Designed to be run on bastion server via SSM AWS-RunRemoteScript command

# Load the variables from config file
source "/home/ssm-user/deductivewebsite-envars.sh"

FILE_TO_LOAD=${1:-""}
DB_DUMP_PATH="${WORKING_DIR}/${FILE_TO_LOAD}"

## Download database dump from S3
aws s3 cp "s3://${DEST_BUCKET}/${DEST_PREFIX}/${FILE_TO_LOAD}" $DB_DUMP_PATH

# Get actual db password from SecretsManager
PASSWORD=$(aws secretsmanager get-secret-value --secret-id $DB_SECRET  --output text --query '[SecretString]' --region=$AWS_REGION 2>/dev/null)

## Load the database locally
mysql -h $DB_HOST -u $DB_USER -p$PASSWORD $DB_NAME < $DB_DUMP_PATH