#!/usr/bin/env python3

"""
(c) Deductive 2020, all rights reserved
"""

from troposphere import Template, Parameter, Equals, \
    constants, Select, GetAZs, Output, Or, Base64, If
from troposphere import Ref, Join, FindInMap, GetAtt
from troposphere.s3 import Bucket, BucketPolicy, BucketEncryption, \
    ServerSideEncryptionRule,  ServerSideEncryptionByDefault, \
    CorsConfiguration, CorsRules
from troposphere.cloudtrail import Trail
from troposphere.iam import Role, Policy, ManagedPolicy
from troposphere.ec2 import VPC, SecurityGroup, Subnet, Tags, \
    RouteTable, SubnetRouteTableAssociation, NatGateway, EIP, \
    Route, InternetGateway, VPCGatewayAttachment, \
    SecurityGroupRule, VPCEndpoint
from troposphere.rds import DBCluster, ScalingConfiguration, \
    DBSubnetGroup
from troposphere.cloudfront import Distribution, DistributionConfig
from troposphere.cloudfront import Origin, DefaultCacheBehavior, ViewerCertificate
from troposphere.cloudfront import ForwardedValues
from troposphere.cloudfront import S3OriginConfig, CustomErrorResponse
from troposphere.cloudfront import CloudFrontOriginAccessIdentity, CloudFrontOriginAccessIdentityConfig
from troposphere.route53 import RecordSet, RecordSetGroup, AliasTarget
from troposphere.cloudformation import Stack
from troposphere.ssm import Association, Targets

import logging
import sys
import os
import json

from deductive_backup_template import DeductiveBastionTemplate

"""
Initialise logger and stdout stream
"""
logger = logging.getLogger(__name__)
stdout = logging.StreamHandler(sys.stdout)
stdout.setFormatter(logging.Formatter('%(message)s'))
stdout.setLevel(logging.INFO)
logger.addHandler(stdout)
logger.setLevel(logging.INFO)

class DeploymentTemplates:

    def __init__(self, long_proj_name, short_proj_name):

        # Note: Module names should use '_' not '-'...
        long_proj_name = long_proj_name.replace(' ', '_')   # replace spaces
        long_proj_name = long_proj_name.replace('-', '_')   # replace dashes
        self._long_project = long_proj_name.lower()
        # ...but some resource names cannot contain '_' so replace with dashes
        self._short_project_dashes = short_proj_name.lower().replace('_', '-')   # replace underscores
        self._long_project_dashes = long_proj_name.lower().replace('_', '-')   # replace underscores
        short_proj_name = short_proj_name.replace(' ', '')   # remove spaces
        short_proj_name = short_proj_name.replace('-', '')   # remove dashes
        self._short_project = short_proj_name.upper()
        self._file_ext = 'json'

    def generate_templates(self, template_path):

        self._template_path = template_path

        """
        Check template_path exists
        """
        if os.path.isdir(self._template_path):
            # Remove existing templates
            filelist = [f for f in os.listdir(
                self._template_path) if f.endswith(self._file_ext)]
            for f in filelist:
                os.remove(os.path.join(self._template_path, f))
        else:
            # Create template path
            os.makedirs(self._template_path)

        """
        Create backup server template
        """
        backup = DeductiveBastionTemplate(
            self._long_project,
            self._short_project
        )
        backup_template = backup.generate_template(template_path)

        """
        Create root template
        """
        root_template = self._generate_root_template(backup_template)

        logger.info("")
        logger.info("GENERATED: {}".format(backup_template))
        logger.info("GENERATED: {}".format(root_template))

    def _add_deployment_stage_parameter(self, template):

        """
        Stack Parameters
            - Deployment Stage
            - Data ingest only
        """
        template.add_parameter(Parameter(
            "DeploymentStage",
            Description="Name of deployment stage required. "
                        "Can't be changed after deployment.",
            Type=constants.STRING,
            Default="STAGING",
            AllowedValues=[
                "STAGING",
                "PRODUCTION",
                "DEV-CLIVE",
            ]
        ))

        """
        Stack Mappings
        """
        template.add_mapping("LowerStage", {
            "STAGING": {"Value": "staging"},
            "PRODUCTION": {"Value": "production"},
            "DEV-CLIVE": {"Value": "dev-clive"},
        })
        template.add_mapping("LowerUnderStage", {
            "STAGING": {"Value": "staging"},
            "PRODUCTION": {"Value": "production"},
            "DEV-CLIVE": {"Value": "dev_clive"},
        })

        template.add_parameter(Parameter(
            "HostedZone",
            Description="Domain name to use for CloudFront",
            Type=constants.STRING
        ))
        template.add_parameter(Parameter(
            "SSLCertArn",
            Description="SSL certificate ARN to use for CloudFront",
            Type=constants.STRING
        ))
        template.add_parameter(Parameter(
            "SubDomain",
            Description="Subdomain for URL",
            Type=constants.STRING
        ))

    def _add_vpc_config_parameters(self, template):

        """
        Stack Parameters
            - VPC CIDR blocks
        """
        template.add_parameter(Parameter(
            "VpcCidrBlock",
            Description="IP address range for VPC. Default: 10.0.0.0/16",
            Type="String",
            Default="10.0.0.0/16"
        ))
        template.add_parameter(Parameter(
            "SubnetCidrBlock1",
            Description="IP address range for subnet 1. Default: 10.0.0.0/24",
            Type="String",
            Default="10.0.0.0/24"
        ))
        template.add_parameter(Parameter(
            "SubnetCidrBlock2",
            Description="IP address range for subnet 2. Default: 10.0.1.0/24",
            Type="String",
            Default="10.0.1.0/24"
        ))
        template.add_parameter(Parameter(
            "SubnetCidrBlock3",
            Description="IP address range for subnet 3. Default: 10.0.2.0/24",
            Type="String",
            Default="10.0.2.0/24"
        ))
        template.add_parameter(Parameter(
            "S3EndpointPrefix",
            Description="The prefix 'pl-xxxxxxx' value for S3 in the deployment \
                region. Use 'aws ec2 describe-prefix-lists'. Default is \
                'pl-68a54001' (us-west-2) or 'pl-63a5400a' (us-east-1)",
            Type="String",
            Default="pl-68a54001"
        ))

    def _add_database_user_parameter(self, template):

        template.add_parameter(Parameter(
            "MasterUsername",
            Description="Master username for database",
            Type=constants.STRING,
            Default='master'
        ))
        template.add_parameter(Parameter(
            "MasterPassword",
            Description="Master password for database",
            Type=constants.STRING,
        ))
        template.add_parameter(Parameter(
            "MasterSecretName",
            Description="Name of secret holding master password for database",
            Type=constants.STRING,
        ))

    def _add_backup_config_parameters(self, template):

        """
        Stack Parameters
        """
        template.add_parameter(Parameter(
            "DmzCidrBlock",
            Description="IP address range for DMZ. Default:10.1.0.0/16",
            Type="String",
            Default="10.1.0.0/16"
        ))
        template.add_parameter(Parameter(
            "DmzSubnetCidrBlock1",
            Description="IP address range DMZ subnet 1. Default: 10.1.0.0/24",
            Type="String",
            Default="10.1.0.0/24"
        ))
        template.add_parameter(Parameter(
            "BackupKeyPairName",
            Description="Name of an existing EC2 KeyPair to enable SSH "
                        "access to the backup instance",
            Type="String",
            Default="deductive-website-django-backup"
        ))
        template.add_parameter(Parameter(
            "BackupImageId",
            Description="ID of an existing EC2 AMI image to use for "
                        "the backup instance",
            Type="String",
            Default="ami-082b5a644766e0e6f" # Amazon Linux 2 AMI (HVM), SSD Volume Type, 64-bit x86
        ))

    def _get_bucket_encryption(self):

        return BucketEncryption(
            ServerSideEncryptionConfiguration=[ServerSideEncryptionRule(
                ServerSideEncryptionByDefault=ServerSideEncryptionByDefault(
                    SSEAlgorithm='AES256'
                )
            )]
        )

    def _generate_root_template(self, backup_template):
        """
        Generate root template
            - primary template
            - deploys common infrastructure
        """
        template_name = 'root'

        t = Template()

        t.set_description(
            "AWS CloudFormation Template: '{}_{}.{}'"
            .format(self._long_project, template_name, self._file_ext))

        """
        Stack Parameters
            - Deployment Stage
        """
        self._add_deployment_stage_parameter(t)
        self._add_vpc_config_parameters(t)
        self._add_database_user_parameter(t)
        self._add_backup_config_parameters(t)

        """
        Conditions
        """
        t.add_condition(
            "ProductionStage",
            Equals(Ref("DeploymentStage"), "PRODUCTION")
        )
        t.add_condition(
            "DeployBackup",
            Or(
                Equals(Ref("DeploymentStage"), "PRODUCTION"),
                Equals(Ref("DeploymentStage"), "STAGING"),
                Equals(Ref("DeploymentStage"), "DEV-CLIVE") #FIXME
            )
        )

        """
        Deploy CloudTrail
        """
        t.add_resource(Bucket(
            "CloudTrailLogsBucket",
            BucketName=Join("-", [
                            self._short_project_dashes,
                            FindInMap("LowerStage",
                                      Ref("DeploymentStage"),
                                      "Value"),
                            "cloudtrail-logs"
                            ]),
            DeletionPolicy="Retain",
            BucketEncryption=self._get_bucket_encryption(),
            Condition="ProductionStage"
        ))
        t.add_resource(BucketPolicy(
            "CloudTrailLogsBucketPolicy",
            PolicyDocument=self._load_policy_document(
                './policies/cloudtrail_logs_bucket_policy.json'),
            Bucket=Ref("CloudTrailLogsBucket"),
            Condition="ProductionStage"
        ))
        t.add_resource(Trail(
            "CloudTrail",
            IsLogging=True,
            S3BucketName=Ref("CloudTrailLogsBucket"),
            DependsOn=["CloudTrailLogsBucketPolicy"],
            Condition="ProductionStage"
        ))

        """
        Deploy deny production update/delete policy. Once PRODUCTION stack is
        deployed add this policy to existing Roles and Users in the AWS account
        to prevent PRODUCTION stack being updated or deleted on command line.
        Only BitBucket master branch should update PRODUCTION.
        """
        t.add_resource(ManagedPolicy(
            "DenyProductionUpdateDeletePolicy",
            ManagedPolicyName=Join("-", [
                self._short_project,
                "Deny",
                Ref("DeploymentStage"),
                "UpdateDelete"
            ]),
            Description="Add this policy to existing Roles and Users to prevent PRODUCTION stack being updated/deleted",
            PolicyDocument=self._load_policy_document(
                './policies/deny_production_updatedelete.json'),
            Condition="ProductionStage"
        ))

        """
        Create VPC
        """
        vpc_resource_name = Join(" ", [
                                 self._short_project,
                                 "VPC for",
                                 Ref("DeploymentStage")])
        t.add_resource(VPC(
            "VirtualPrivateCloud",
            CidrBlock=Ref("VpcCidrBlock"),
            EnableDnsSupport=True,
            EnableDnsHostnames=True,
            Tags=Tags(Name=vpc_resource_name)
        ))
        # The security group allows no incoming traffic,
        # other than from the VPC itself,
        # but does allow outgoing to the Internet
        t.add_resource(SecurityGroup(
            "SecurityGroup",
            GroupName=vpc_resource_name,
            GroupDescription=vpc_resource_name,
            VpcId=Ref("VirtualPrivateCloud"),
            Tags=Tags(Name=vpc_resource_name),
            SecurityGroupEgress=[
                SecurityGroupRule(
                    DestinationPrefixListId=Ref("S3EndpointPrefix"),
                    IpProtocol="-1",
                    Description=vpc_resource_name
                ),
                SecurityGroupRule(
                    CidrIp="0.0.0.0/0",
                    IpProtocol="-1",
                    Description=vpc_resource_name
                ),
            ],
            SecurityGroupIngress=[
                SecurityGroupRule(
                    CidrIp=Ref("VpcCidrBlock"),
                    IpProtocol="-1",
                    Description=vpc_resource_name
                ),
                SecurityGroupRule(
                    CidrIp=Ref("DmzCidrBlock"),
                    IpProtocol="TCP",
                    FromPort='3306',
                    ToPort='3306',
                    Description=vpc_resource_name
                )
            ],
            DependsOn=['VirtualPrivateCloud']
        ))
        # AWS recommend using at least 2 subnets, each in a
        # different AZ, to run in high availability mode.
        t.add_resource(Subnet(
            "PrivateSubnet1",
            VpcId=Ref("VirtualPrivateCloud"),
            CidrBlock=Ref("SubnetCidrBlock1"),
            AvailabilityZone=Select('0', GetAZs('')),
            Tags=Tags(Name=Join(" ", ['PRIVATE', vpc_resource_name])),
            DependsOn=['VirtualPrivateCloud']
        ))
        t.add_resource(Subnet(
            "PrivateSubnet2",
            VpcId=Ref("VirtualPrivateCloud"),
            CidrBlock=Ref("SubnetCidrBlock2"),
            AvailabilityZone=Select('1', GetAZs('')),
            Tags=Tags(Name=Join(" ", ['PRIVATE', vpc_resource_name])),
            DependsOn=['VirtualPrivateCloud']
        ))
        # An endpoint is how resources such as S3 and SNS connect
        # to the VPC to avoid data going over the Internet
        # Lambda access to the VPC is configured separately
        t.add_resource(VPCEndpoint(
            "VPCEndpointS3",
            VpcId=Ref("VirtualPrivateCloud"),
            ServiceName=Join(".", [
                "com",
                "amazonaws",
                Ref("AWS::Region"),
                "s3"
            ]),
            VpcEndpointType="Gateway",
            RouteTableIds=[Ref("PrivateRouteTable")],
            DependsOn=['VirtualPrivateCloud', 'PrivateRouteTable']
        ))
        t.add_resource(VPCEndpoint(
            "VPCEndpointSecrets",
            VpcId=Ref("VirtualPrivateCloud"),
            ServiceName=Join(".", [
                "com",
                "amazonaws",
                Ref("AWS::Region"),
                "secretsmanager"
            ]),
            VpcEndpointType="Interface",
            PrivateDnsEnabled=True,
            SecurityGroupIds=[Ref("SecurityGroup")],
            SubnetIds=[Ref("PrivateSubnet1"), Ref("PrivateSubnet2")],
            DependsOn=['VirtualPrivateCloud', 'SecurityGroup',
                       'PrivateSubnet1', 'PrivateSubnet2']
        ))
        t.add_resource(VPCEndpoint(
            "VPCEndpointEC2",
            VpcId=Ref("VirtualPrivateCloud"),
            ServiceName=Join(".", [
                "com",
                "amazonaws",
                Ref("AWS::Region"),
                "ec2"
            ]),
            VpcEndpointType="Interface",
            PrivateDnsEnabled=True,
            SecurityGroupIds=[Ref("SecurityGroup")],
            SubnetIds=[Ref("PrivateSubnet1"), Ref("PrivateSubnet2")],
            DependsOn=['VirtualPrivateCloud', 'SecurityGroup',
                       'PrivateSubnet1', 'PrivateSubnet2']
        ))
        t.add_resource(VPCEndpoint(
            "VPCEndpointEC2Messages",
            VpcId=Ref("VirtualPrivateCloud"),
            ServiceName=Join(".", [
                "com",
                "amazonaws",
                Ref("AWS::Region"),
                "ec2messages"
            ]),
            VpcEndpointType="Interface",
            PrivateDnsEnabled=True,
            SecurityGroupIds=[Ref("SecurityGroup")],
            SubnetIds=[Ref("PrivateSubnet1"), Ref("PrivateSubnet2")],
            DependsOn=['VirtualPrivateCloud', 'SecurityGroup',
                       'PrivateSubnet1', 'PrivateSubnet2']
        ))
        # A Route Table is required to allow the VPC access to the endpoints
        t.add_resource(RouteTable(
            "PrivateRouteTable",
            VpcId=Ref("VirtualPrivateCloud"),
            Tags=Tags(Name=Join(" ", ['PRIVATE', vpc_resource_name])),
            DependsOn=['VirtualPrivateCloud']
        ))
        t.add_resource(SubnetRouteTableAssociation(
            'PrivateSubnetRouteTableAssociation1',
            SubnetId=Ref('PrivateSubnet1'),
            RouteTableId=Ref('PrivateRouteTable'),
            DependsOn=['PrivateRouteTable', 'PrivateSubnet1']
        ))
        t.add_resource(SubnetRouteTableAssociation(
            'PrivateSubnetRouteTableAssociation2',
            SubnetId=Ref('PrivateSubnet2'),
            RouteTableId=Ref('PrivateRouteTable'),
            DependsOn=['PrivateRouteTable', 'PrivateSubnet2']
        ))
        """
        Add NAT Gateway for Internet access
        """
        t.add_resource(Subnet(
            "PublicSubnet",
            CidrBlock=Ref("SubnetCidrBlock3"),
            MapPublicIpOnLaunch=True,
            VpcId=Ref("VirtualPrivateCloud"),
            Tags=Tags(Name=Join(" ", ['PUBLIC', vpc_resource_name])),
            DependsOn=['VirtualPrivateCloud']
        ))
        t.add_resource(RouteTable(
            'PublicRouteTable',
            VpcId=Ref("VirtualPrivateCloud"),
            Tags=Tags(Name=Join(" ", ['PUBLIC', vpc_resource_name])),
            DependsOn=['VirtualPrivateCloud']
        ))
        t.add_resource(SubnetRouteTableAssociation(
            'PublicSubnetRouteTableAssociation',
            SubnetId=Ref('PublicSubnet'),
            RouteTableId=Ref('PublicRouteTable'),
            DependsOn=['PublicRouteTable', 'PublicSubnet']
        ))
        t.add_resource(EIP(
            "IPAddress",
            Domain="vpc",
        ))
        # Need a NAT Gateway in Public subnet with route from Private subnet
        t.add_resource(NatGateway(
            "NatGateway",
            AllocationId=GetAtt("IPAddress", "AllocationId"),
            SubnetId=Ref("PublicSubnet"),
            DependsOn=['PublicSubnet', 'IPAddress']
        ))
        t.add_resource(Route(
            "NatRoute",
            RouteTableId=Ref("PrivateRouteTable"),
            DestinationCidrBlock='0.0.0.0/0',
            NatGatewayId=Ref("NatGateway"),
            DependsOn=['NatGateway', 'PrivateRouteTable']
        ))
        # Need an Internet Gateway on Public subnet
        t.add_resource(InternetGateway(
            "InternetGateway",
            DependsOn=['VirtualPrivateCloud']
        ))
        t.add_resource(VPCGatewayAttachment(
            "IGAttachment",
            VpcId=Ref("VirtualPrivateCloud"),
            InternetGatewayId=Ref("InternetGateway"),
            DependsOn=['VirtualPrivateCloud', 'InternetGateway']
        ))
        t.add_resource(Route(
            'PublicDefaultRoute',
            RouteTableId=Ref('PublicRouteTable'),
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=Ref('InternetGateway'),
            DependsOn=['IGAttachment', 'PublicRouteTable']
        ))

        """
        Deploy S3 bucket for static files
        """
        bucket_name = Join("-", [
            self._long_project_dashes,
            FindInMap(
                "LowerStage",
                Ref("DeploymentStage"),
                "Value"),
        ])
        bucket_resource = "StaticBucket"
        t.add_resource(Bucket(
            bucket_resource,
            BucketName=bucket_name,
            BucketEncryption=self._get_bucket_encryption(),
            CorsConfiguration=CorsConfiguration(
                CorsRules=[CorsRules(
                    AllowedOrigins=["*"],
                    AllowedMethods=["GET"],
                )]
            )
        ))

        """
        Deploy CloudFront distribution
        """
        t.add_resource(CloudFrontOriginAccessIdentity(
            "AccessIdentity",
            CloudFrontOriginAccessIdentityConfig=CloudFrontOriginAccessIdentityConfig(
                Comment=Join("-", ["access-identity", bucket_name])
            ),
            DependsOn=[bucket_resource]
        ))
        t.add_resource(BucketPolicy(
            bucket_resource + "BucketPolicy",
            PolicyDocument=self._load_policy_document(
                './policies/bucket_for_cloudfront_policy.json',
                Join(" ",
                     ["arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity",
                      Ref("AccessIdentity")]),
                Join("", [GetAtt(bucket_resource, 'Arn'), "/*"])
            ),
            Bucket=Ref(bucket_resource),
            DependsOn=[bucket_resource,
                       "AccessIdentity"],
        ))
        web_name = Join("", [
            Ref("SubDomain"),
            ".",
            Ref("HostedZone")
        ])
        t.add_resource(Distribution(
            "WebDistribution",
            DistributionConfig=DistributionConfig(
                Aliases=[web_name],
                Origins=[Origin(Id=bucket_name,
                                DomainName=GetAtt(bucket_resource, 'RegionalDomainName'),
                                S3OriginConfig=S3OriginConfig(
                                    OriginAccessIdentity=Join("", ["origin-access-identity/cloudfront/",
                                                                   Ref("AccessIdentity")])
                                ))],
                DefaultCacheBehavior=DefaultCacheBehavior(
                    TargetOriginId=bucket_name,
                    ForwardedValues=ForwardedValues(
                        QueryString=False
                    ),
                    ViewerProtocolPolicy="redirect-to-https",
                    AllowedMethods=["GET", "HEAD", "OPTIONS"],
                    Compress=True),
                Enabled=True,
                HttpVersion='http2',
                DefaultRootObject='index.html',
                ViewerCertificate=ViewerCertificate(
                    AcmCertificateArn=Ref("SSLCertArn"),
                    SslSupportMethod="sni-only",
                    MinimumProtocolVersion="TLSv1.1_2016"
                ),
                #CustomErrorResponses=self._get_custom_error_responses()
            ),
            DependsOn=[bucket_resource,
                       "AccessIdentity"],
        ))

        """
        Deploy DNS alias
        """
        t.add_resource(RecordSetGroup(
            "Record",
            HostedZoneName=Join("", [Ref("HostedZone"), "."]),
            RecordSets=[
                RecordSet(
                    Name=Join("", [web_name, "."]),
                    Type="A",
                    AliasTarget=AliasTarget(
                        DNSName=GetAtt("WebDistribution", "DomainName"),
                        HostedZoneId=constants.CLOUDFRONT_HOSTEDZONEID
                    )
                )
            ],
            DependsOn=["WebDistribution"],
        ))

        """
        Deploy Aurora Database
        """
        t.add_resource(DBSubnetGroup(
            "DBSubnetGroup",
            DBSubnetGroupDescription="Subnets available for the RDS DB Instance",
            SubnetIds=[Ref("PrivateSubnet1"), Ref("PrivateSubnet2")],
            DependsOn = ['PrivateSubnet1', 'PrivateSubnet2']
        ))
        t.add_resource(DBCluster(
            "AuroraCluster",
            Engine='aurora',
            EngineMode='serverless',
            DatabaseName=self._short_project.lower(),
            DBClusterIdentifier=Join('-', [
                self._long_project_dashes,
                FindInMap("LowerStage",
                          Ref("DeploymentStage"),
                          "Value"),
                'dbcluster'
            ]),
            MasterUsername=Ref('MasterUsername'),
            MasterUserPassword=Ref('MasterPassword'),
            StorageEncrypted=True,
            ScalingConfiguration=ScalingConfiguration(
                AutoPause=False,
                MinCapacity=2,
                MaxCapacity=8
            ),
            DBSubnetGroupName=Ref("DBSubnetGroup"),
            VpcSecurityGroupIds=[GetAtt("SecurityGroup", "GroupId")],
            DependsOn=['DBSubnetGroup']
        ))

        """
        Deploy backup server template
        """
        ssh_subdomain=Join("-", [
            "backup",
            FindInMap(
                "LowerStage",
                Ref("DeploymentStage"),
                "Value")
        ])
        ssh_url=Join(".", [
            ssh_subdomain,
            Ref("HostedZone")
        ])
        working_dir = '/home/ssm-user'
        config_file = Join('', [
            working_dir,
            '/',
            self._short_project.lower(),
            '-envars.sh'
        ])
        t.add_resource(Stack(
            "BackupServerTemplate",
            TemplateURL=backup_template,
            Parameters={
                "DeploymentStage": Ref("DeploymentStage"),
                "LowerStage": FindInMap(
                    "LowerStage",
                    Ref("DeploymentStage"),
                    "Value"),
                "DmzCidrBlock": Ref("DmzCidrBlock"),
                "DmzSubnetCidrBlock1": Ref("DmzSubnetCidrBlock1"),
                "BastionKeyPairName": Ref("BackupKeyPairName"),
                "BastionImageId": Ref("BackupImageId"),
                "VirtualPrivateCloud": Ref("VirtualPrivateCloud"),
                "VpcCidrBlock": Ref("VpcCidrBlock"),
                "VpcRouteTable": Ref("PrivateRouteTable"),
                "HostedZone": Ref("HostedZone"),
                "SubDomain": ssh_subdomain,
                "UserData": Base64(Join('', [
                    "#!/bin/bash -xe\n",
                    "yum update -y\n",
                    "yum install -y mysql\n",
                    "echo DB_HOST=", GetAtt('AuroraCluster', 'Endpoint.Address'), " > ", config_file, "\n",
                    "echo DB_USER=", Ref('MasterUsername'), " >> ", config_file, "\n",
                    "echo DB_SECRET=", Ref('MasterSecretName'), " >> ", config_file, "\n",
                    "echo DB_NAME=", self._short_project.lower(), " >> ", config_file, "\n",
                    "echo DEPLOY_STAGE=", Ref("DeploymentStage"), " >> ", config_file, "\n",
                    "echo AWS_REGION=", Ref("AWS::Region"), " >> ", config_file, "\n",
                    "echo WORKING_DIR=", working_dir, " >> ", config_file, "\n",
                    "echo DEST_BUCKET=", self._long_project_dashes, '-deploy', " >> ", config_file, "\n",
                    "echo DEST_PREFIX=", 'database/backups', " >> ", config_file, "\n",
                    '\n',
                ]))
            },
            DependsOn=['VirtualPrivateCloud',
                       "PrivateRouteTable"],
            Condition="DeployBackup"
        ))

        """
        Deploy database snapshot event
        """
        script_name="deductive_export_database.sh"
        base_path="https://s3.amazonaws.com/deductive-website-deploy/database/scripts/"
        script_path=Join("", [
            base_path,
            Ref("DeploymentStage"),
            '/',
            script_name
        ])
        source_info=Join("", [
            "{\"path\": \"",
            script_path,
            "\"}"
        ])
        params={}
        params["sourceType"]=["S3"]
        params["sourceInfo"]=[source_info]
        params["commandLine"]=["\"{}\"".format(script_name)]
        t.add_resource(Association(
            "BackupTriggerRule",
            AssociationName=Join("-", [
                Ref("DeploymentStage"),
                "Deductive-Snapshot-Trigger",
                "CloudWatch-Event"
            ]),
            Name="AWS-RunRemoteScript",
            Parameters=params,
            ScheduleExpression="rate(1 day)",
            Targets=[Targets(
                Key='tag:Name',
                Values=[GetAtt('BackupServerTemplate', 'Outputs.BastionServerTagName')]
            )],
            DependsOn=["BackupServerTemplate"],
            Condition="DeployBackup"
        ))

        """
        Output Backup Server details
        """
        t.add_output([
            Output(
                "BackupServerAddress",
                Description="Host name of backup server",
                Value=ssh_url,
                Condition="DeployBackup"
            ),
        ])

        """
        Output DB and CF details
        """
        t.add_output([
            Output(
                "DatabaseUsername",
                Description="Username for master database user",
                Value=Ref('MasterUsername')
            ),
            Output(
                "DatabasePassword",
                Description="Password for master database user",
                Value=Ref('MasterPassword')
            ),
            Output(
                "DatabaseName",
                Description="Database name",
                Value=self._short_project.lower()
            ),
            Output(
                "DatabaseHost",
                Description="Endpoint host for database",
                Value=GetAtt('AuroraCluster', 'Endpoint.Address')
            ),
            Output(
                "DatabasePort",
                Description="Endpoint port for database",
                Value=GetAtt('AuroraCluster', 'Endpoint.Port')
            ),
            Output(
                "SubnetIds",
                Description="VPC info for database",
                Value=Join(',', [
                    Ref("PrivateSubnet1"),
                    Ref("PrivateSubnet2")
                ])
            ),
            Output(
                "SecurityGroupId",
                Description="VPC info for database",
                Value=Ref('SecurityGroup')
            ),
            Output(
                "CloudFrontDistrib",
                Description="CloudFront disytribution ID of GUI website",
                Value=Ref("WebDistribution"),
            ),
        ])

        """
        Create the template
        """
        return self._save_template(template_name, t.to_json())


    def _get_custom_error_responses(self):

        return [
            CustomErrorResponse(
                ErrorCachingMinTTL=300,
                ErrorCode=403,
                ResponseCode=200,
                ResponsePagePath="/index.html"
            ),
            CustomErrorResponse(
                ErrorCachingMinTTL=300,
                ErrorCode=404,
                ResponseCode=200,
                ResponsePagePath="/index.html"
            ),
        ]

    def _load_policy_document(self, inpath, param1='', param2=''):

        policy = None

        with open(inpath) as infile:
            policy = eval(infile.read())

        return policy

    def _save_template(self, name, outstr):

        outname = "{}_{}.{}".format(
            self._long_project,
            name,
            self._file_ext)

        with open(self._template_path + '/' + outname, 'w') as outfile:
            outfile.write(outstr)

        return outname


if __name__ == "__main__":

    """
    Get command line arguments
    """
    if len(sys.argv) != 3:

        logger.info("Cannot generate templates. Incorrect arguments for " +
                    str(sys.argv[0]))

    else:

        # Project names
        long_proj_name = str(sys.argv[1])  # e.g. 'Something Really Great'
        short_proj_name = str(sys.argv[2])  # e.g. 'SRG'

        """
        Generate the templates
        """
        deployment = DeploymentTemplates(long_proj_name, short_proj_name)
        deployment.generate_templates('./templates')

