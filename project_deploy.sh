#!/bin/bash

# (c) Deductive 2020, all rights reserved

# Optional parameters
AWS_STAGE=${1:-"STAGING"}
COMMAND=${2:-"deploy"}
PROFILE=${3:-""}
REGION=${4:-"us-west-2"}

COMMAND_LWR=`echo "$COMMAND" | tr '[:upper:]' '[:lower:]'`
AWS_STAGE_LWR=`echo "$AWS_STAGE" | tr '[:upper:]' '[:lower:]'`

# These could also be parameterized if required
PROJECT="deductive-website"
PROJECT_LONG="deductive-website"
SSLCERT="arn:aws:acm:us-east-1:538486622005:certificate/4d773105-bf94-4b33-a267-5203b0aca23f"
DOMAIN="deductive.com"
if [ "${AWS_STAGE_LWR}" == 'production' ]; then
    SUBDOMAIN="www2"
    STATICSUB="static"
elif [ "${AWS_STAGE_LWR}" == 'staging' ]; then
    SUBDOMAIN="${AWS_STAGE_LWR}"
    STATICSUB="static-${AWS_STAGE_LWR}"
else
    SUBDOMAIN="www-${AWS_STAGE_LWR}"
    STATICSUB="static-${AWS_STAGE_LWR}"
fi

if [[ -z $PROFILE ]]; then

    ZAPPA_PROFILE='zappa'
    # If no profile provided we need to create one from AWS_* envars for Zappa to work
    (echo $AWS_ACCESS_KEY_ID; echo $AWS_SECRET_ACCESS_KEY; echo $REGION; echo ;) | aws configure --profile $ZAPPA_PROFILE 1>/dev/null
    PROFILE=$ZAPPA_PROFILE
fi
if [[ ! -z $PROFILE ]]; then
    # $PROFILE was given
    PROFILE_OPT=" --profile $PROFILE"
    echo ''
    echo "Using: '$PROFILE_OPT'"
    # Create envars
    export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id $PROFILE_OPT)
    export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key $PROFILE_OPT)
fi
if [[ ! -z $REGION ]]; then
    # $REGION was given
    REGION_OPT=" --region $REGION"
    echo "Using: '$REGION_OPT'"
fi
PARAM_OVERRIDES="DeploymentStage=${AWS_STAGE} HostedZone=${DOMAIN} SSLCertArn=${SSLCERT} SubDomain=${STATICSUB}"

# Prepare other data
STACK_NAME="${PROJECT_LONG}-aws-${AWS_STAGE_LWR}"
DEPLOY_BUCKET="${PROJECT_LONG}-deploy"
STATIC_BUCKET="${PROJECT_LONG}-${AWS_STAGE_LWR}"
TEMPLATE_EXT="json"
TEMPLATE_KEY="templates"
ROOT_TEMPLATE="./${TEMPLATE_KEY}/${PROJECT_LONG//-/_}_root.${TEMPLATE_EXT}"
SCRIPTS_DIR="scripts"
S3_PACKAGE_KEY='packages'
export FRAMEWORK="Zappa"

DJANGO_DIR='./'
ZAPPA_SETTINGS='zappa_settings.json'
ZAPPA_STAGE=${AWS_STAGE_LWR//-/_}

DATABASE_MASTER_PW_SECRET_NAME="${PROJECT}/${AWS_STAGE_LWR}/database/master/password"
DJANGO_ADMIN_PW_SECRET_NAME="${PROJECT}/${AWS_STAGE_LWR}/django/admin/password"
DJANGO_SECRET_KEY_NAME="${PROJECT}/${AWS_STAGE_LWR}/django/secretkey"

PW_LENGTH=10
KEY_LENGTH=50

AWS_STAGENAME_KEY="$PROJECT-stage-name"

CWD=$(pwd)

export AWS_DEFAULT_REGION=$REGION
aws configure set default.region $AWS_DEFAULT_REGION

# Define helper functions

check_for_error() {

    if [ "$1" -ne 0 ]; then
        echo ''
        echo "*********************"
        echo "** ERROR"
        echo "** $2"
        echo "*********************"
        echo ''
        exit $1
    fi
}

create_secretsmanager_pw () {

    SECRET_NAME=$1
    PW_LENGTH=$2
    PASSWORD=$(aws secretsmanager get-secret-value --secret-id $SECRET_NAME  --output text --query '[SecretString]' $PROFILE_OPT $REGION_OPT 2>/dev/null)

    if [[ $? -ne 0 ]]; then
        # Create password secret
        PASSWORD=$(aws secretsmanager get-random-password --exclude-punctuation --password-length $PW_LENGTH --output text --query '[RandomPassword]' $PROFILE_OPT $REGION_OPT)
        CREATE=$(aws secretsmanager create-secret --name $SECRET_NAME --secret-string $PASSWORD $PROFILE_OPT $REGION_OPT)
    fi

    echo $PASSWORD
}

invalidate_cache () {

    # Invalidate cache
    echo ''
    echo "INVALIDATE CLOUDFRONT CACHE..."
    aws cloudfront create-invalidation --distribution-id $DISTRIBID --paths '/*' $PROFILE_OPT $REGION_OPT > /dev/null 2>&1
    check_for_error $? "Failed to invalidate cache"
}

start_venv() {

    # Virtual env needed for Zappa deployment
    echo ''
    virtualenv venv
    source venv/bin/activate
    pip3 install --upgrade -r ./requirements.txt
    pip3 install mysqlclient==1.3.14
    cp -r ./precompiled/lambda_packages ./venv/lib/python3.6/site-packages
    cd $DJANGO_DIR
    cp /usr/lib64/mysql/libmysqlclient.so.18 .
}

stop_venv() {

    rm ./libmysqlclient.so.18
    deactivate
    cd ..
}

deploy_django () {

    start_venv

    # Generate a new password in secrets manager to use for db superuser
    SU_PASS=$(create_secretsmanager_pw $DJANGO_ADMIN_PW_SECRET_NAME $PW_LENGTH)

    # Generate a new secret key for Django
    SECRETKEY=$(create_secretsmanager_pw $DJANGO_SECRET_KEY_NAME $KEY_LENGTH)
    export SECRET_KEY=$SECRETKEY

    echo "CREATING ZAPPA SETTINGS..."
    python3 ./generate_zappa_settings.py \
        $ZAPPA_SETTINGS $PROJECT_LONG $AWS_STAGE $ZAPPA_STAGE \
        $PROFILE $REGION \
        $DBNAME $DBUSER $DBPWORD $DBHOST $DBPORT \
        $SUBNETIDS $SECURITYGROUPID \
        $SU_PASS $DOMAIN $SUBDOMAIN $STATICSUB \
        $SSLCERT $SECRETKEY

    # Is this stack already deployed?
    STATUS=$(zappa status $ZAPPA_STAGE 2>/dev/null)
    if [[ $STATUS =~ $ZAPPA_STAGE ]]; then
        echo "PERFORM AN UPDATE..."
        zappa update $ZAPPA_STAGE
    else
        echo "NEW DEPLOYMENT..."
        zappa deploy $ZAPPA_STAGE
    fi

    echo "UPLOAD STATIC WEB FILES..."
    export STATIC_S3_BUCKET=$STATIC_BUCKET
    python3 manage.py collectstatic --noinput

    #echo "INITIALISE THE DATABASE..."
    #zappa manage "${ZAPPA_STAGE}" "makemigrations"
    #zappa manage "${ZAPPA_STAGE}" "migrate"

    echo "ENABLING SSL CERTIFICATION..."
    zappa certify --yes

    echo "CREATING SUPERUSER..."
    zappa invoke --raw $ZAPPA_STAGE "from django.contrib.auth.models import User; User.objects.filter(username='admin').delete(); User.objects.create_superuser('admin', 'admin@yourdomain.com', '${SU_PASS}')"

    zappa status $ZAPPA_STAGE

    stop_venv
}

undeploy_django () {

    start_venv
    echo "DELETE DEPLOYMENT..."
    zappa manage $ZAPPA_STAGE "flush --noinput"
    echo "y" | zappa undeploy $ZAPPA_STAGE
    stop_venv
}

check_stage () {

    # Only allow STAGING and PRODUCTION deployments from Bitbucket pipeline
    if [[ $AWS_STAGE_LWR = "staging" ]] || [[ $AWS_STAGE_LWR = "production" ]]; then
        # We can tell if we're in a pipeline as the `CI` key will be defined
        if [[ -z "${CI-}" ]]; then
            echo ''
            echo "*********************"
            echo "***** '$AWS_STAGE' stage can only be deployed from Bitbucket Pipeline!"
            echo "*********************"
            echo ''
            exit
        fi
    fi

}

deploy_stack () {

    # Make sure the templates are up-to-date
    echo ''
    echo "CREATING TEMPLATES..."
    python3 generate_templates.py $PROJECT_LONG $PROJECT

    # Create deploy bucket if it doesn't already exist
    aws s3 mb s3://$DEPLOY_BUCKET $PROFILE_OPT $REGION_OPT 2>/dev/null

    # Upload the remote scripts
    SCRIPTS="deductive_export_database.sh deductive_import_database.sh"
    for SCRIPT in $SCRIPTS; do
        if [[ $AWS_STAGE_LWR = "production" ]]; then
            aws s3 cp "${SCRIPTS_DIR}/${SCRIPT}" "s3://${DEPLOY_BUCKET}/database/${SCRIPTS_DIR}/" $PROFILE_OPT $REGION_OPT
        else
            aws s3 cp "${SCRIPTS_DIR}/${SCRIPT}" "s3://${DEPLOY_BUCKET}/database/${SCRIPTS_DIR}/${AWS_STAGE}/" $PROFILE_OPT $REGION_OPT
        fi
    done

    # Package the Templates and Lambda code
    for template in ./$TEMPLATE_KEY/*.$TEMPLATE_EXT; do
        echo ''
        echo "PACKAGING: $template"
        aws cloudformation package --template-file $template --s3-bucket $DEPLOY_BUCKET --s3-prefix $S3_PACKAGE_KEY --output-template-file $template --use-json $PROFILE_OPT $REGION_OPT
    done
    check_for_error $? "Failed to create package"

    # Deploy or update the AWS infrastructure
    echo ''
    echo "...CREATING/UPDATING CLOUDFORMATION STACKS..."
    PW=$(create_secretsmanager_pw $DATABASE_MASTER_PW_SECRET_NAME $PW_LENGTH)
    PARAM_OVERRIDES=$PARAM_OVERRIDES" MasterPassword=${PW}"
    PARAM_OVERRIDES=$PARAM_OVERRIDES" MasterSecretName=${DATABASE_MASTER_PW_SECRET_NAME}"
    aws cloudformation deploy --template-file $ROOT_TEMPLATE --s3-bucket $DEPLOY_BUCKET --s3-prefix $TEMPLATE_KEY --stack-name $STACK_NAME --parameter-overrides $PARAM_OVERRIDES --capabilities CAPABILITY_NAMED_IAM $PROFILE_OPT $REGION_OPT

    # Add termination protection for STAGING and PRODUCTION stacks
    if [[ $AWS_STAGE_LWR = "test" ]] || [[ $AWS_STAGE_LWR = "staging" ]] || [[ $AWS_STAGE_LWR = "production" ]]; then
        aws cloudformation update-termination-protection --enable-termination-protection --stack-name $STACK_NAME $PROFILE_OPT $REGION_OPT
        check_for_error $? "Failed to update termination protection"
    fi

    # Add to profile for access by tests
    aws configure set default.$AWS_STAGENAME_KEY $AWS_STAGE $PROFILE_OPT $REGION_OPT
    AWS_STAGENAME=$(aws configure get default.$AWS_STAGENAME_KEY $PROFILE_OPT $REGION_OPT)
    check_for_error $? "Failed to set configuration"
    
    get_stack_output
}

get_stack_output () {

    # Get outputs from root stack
    DBNAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --output text --query 'Stacks[*].Outputs[?OutputKey==`DatabaseName`].[OutputValue]' $PROFILE_OPT $REGION_OPT)
    DBUSER=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --output text --query 'Stacks[*].Outputs[?OutputKey==`DatabaseUsername`].[OutputValue]' $PROFILE_OPT $REGION_OPT)
    DBPWORD=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --output text --query 'Stacks[*].Outputs[?OutputKey==`DatabasePassword`].[OutputValue]' $PROFILE_OPT $REGION_OPT)
    DBHOST=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --output text --query 'Stacks[*].Outputs[?OutputKey==`DatabaseHost`].[OutputValue]' $PROFILE_OPT $REGION_OPT)
    DBPORT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --output text --query 'Stacks[*].Outputs[?OutputKey==`DatabasePort`].[OutputValue]' $PROFILE_OPT $REGION_OPT)
    SUBNETIDS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --output text --query 'Stacks[*].Outputs[?OutputKey==`SubnetIds`].[OutputValue]' $PROFILE_OPT $REGION_OPT)
    SECURITYGROUPID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --output text --query 'Stacks[*].Outputs[?OutputKey==`SecurityGroupId`].[OutputValue]' $PROFILE_OPT $REGION_OPT)
    DISTRIBID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --output text --query 'Stacks[*].Outputs[?OutputKey==`CloudFrontDistrib`].[OutputValue]' $PROFILE_OPT $REGION_OPT)
}

delete_stack () {

    echo ''
    echo ''
    echo "DELETING CLOUDFORMATION STACK '$STACK_NAME'..."
    echo ''

    # Check Termination Protection
    TERMPROTECT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --output text --query 'Stacks[*].[EnableTerminationProtection]' $PROFILE_OPT $REGION_OPT)

    if [[ $TERMPROTECT = "False" ]]; then

        # Delete the stack
        aws cloudformation delete-stack --stack-name $STACK_NAME --output text $PROFILE_OPT $REGION_OPT
        check_for_error $? "Failed to delete stack"

        # Remove the stage name from profile
        aws configure set default.$AWS_STAGENAME_KEY '' $PROFILE_OPT $REGION_OPT
        check_for_error $? "Failed to update config"

        # Wait for stack delete to complete
        aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME $PROFILE_OPT $REGION_OPT
        check_for_error $? "Failed to wait for stack deletion"

    else
        echo "CAN'T DELETE CLOUDFORMATION STACK '$STACK_NAME'"
    fi
}

# Check what the user wants

check_stage

echo ''
if [[ $COMMAND_LWR = "delete" ]]; then
    EXPLAIN="This will *DELETE* the '$STACK_NAME' CloudFormation stack."
elif [[ $COMMAND_LWR = "delete-django" ]]; then
    EXPLAIN="This will *DELETE* the '${PROJECT}-zappa-${AWS_STAGE_LWR}' Django stack AND database."
elif [[ $COMMAND_LWR = "deploy" ]] || [[ $COMMAND_LWR = "deploy-stack" ]]; then
    EXPLAIN="This will copy the latest code to the '$DEPLOY_BUCKET' S3 bucket and create/update the '$STACK_NAME' CloudFormation stack."
fi

if [[ ! -z $EXPLAIN ]]; then

    read -p "$EXPLAIN Are you sure you want to continue? " -n 1 -r

    # Do what the user wants
    if [[ $REPLY =~ ^[Yy]$ ]]; then

        if [[ $COMMAND_LWR = "delete" ]]; then
            undeploy_django
            delete_stack
        elif [[ $COMMAND_LWR = "delete-django" ]]; then
            undeploy_django
        elif [[ $COMMAND_LWR = "deploy" ]]; then
            deploy_stack
            deploy_django
            invalidate_cache
        elif [[ $COMMAND_LWR = "deploy-stack" ]]; then
            deploy_stack
            invalidate_cache
        fi

        echo ''
        echo "*********************"
        echo "***** COMPLETED *****"
        echo "*********************"
        echo ''

    else

        echo ''
        echo "***** QUIT *****"
        echo ''

    fi

else

    if [[ $COMMAND_LWR = "test" ]]; then

        echo ''

    else
        echo ''
        echo "***************************"
        echo "***** UNKNOWN COMMAND *****"
        echo "***************************"
        exit
    fi

fi
