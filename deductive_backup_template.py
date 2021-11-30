#!/usr/bin/env python3

"""
(c) Deductive 2020, all rights reserved
-----------------------------------------
This code is licensed under MIT license

Redistribution & use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
    this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.
    * Neither the name of the Deductive Limited nor the names of
    its contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from troposphere import Template, Parameter, Output, constants, Select, GetAZs
from troposphere import Ref, Join, GetAtt
from troposphere.ec2 import VPC, SecurityGroup, Subnet, Tags, \
    RouteTable, SubnetRouteTableAssociation, EIP, \
    Route, InternetGateway, VPCGatewayAttachment, Instance, \
    VPCPeeringConnection, SecurityGroupRule, VPCEndpoint
from troposphere.route53 import RecordSet, RecordSetGroup
from troposphere.iam import Role, InstanceProfile

import logging
import os

"""
Initialise logger
"""
logger = logging.getLogger("deductive.tools.aws.backup")


class DeductiveBastionTemplate:

    def __init__(self, long_project_name, short_project_name):

        # Note: Module names should use '_' not '-'...
        self._file_project = long_project_name
        self._short_project = short_project_name
        # ...but bucket names cannot contain '_' so replace for buckets
        self._dash_project = self._file_project.replace('_', '-')
        self._file_ext = 'json'

    def generate_template(self, template_path):

        self._template_path = template_path

        """
        Create backup server template
        """
        backup_template = self._generate_backup_template()

        logger.info("")
        logger.info("GENERATED: {}".format(backup_template))

        return backup_template

    def _generate_backup_template(self):

        """
        Generate Bastion Server template
        """
        template_name = 'backup'

        t = Template()

        t.set_description(
            "AWS CloudFormation Template: '{}_{}.{}'"
            .format(self._file_project, template_name, self._file_ext))

        """
        Stack Parameters
        """
        t.add_parameter(Parameter(
            "DeploymentStage",
            Description="Name of deployment stage required",
            Type=constants.STRING,
        ))
        t.add_parameter(Parameter(
            "LowerStage",
            Description="Lower case name of deployment stage required",
            Type=constants.STRING,
        ))
        t.add_parameter(Parameter(
            "DmzCidrBlock",
            Description="IP address range for DMZ. Default:10.1.0.0/16",
            Type=constants.STRING,
            Default="10.1.0.0/16"
        ))
        t.add_parameter(Parameter(
            "DmzSubnetCidrBlock1",
            Description="IP address range DMZ subnet 1. Default: 10.1.0.0/24",
            Type=constants.STRING,
            Default="10.1.0.0/24"
        ))
        t.add_parameter(Parameter(
            "DmzSubnetCidrBlock2",
            Description="IP address range DMZ subnet 2. Default: 10.1.1.0/24",
            Type=constants.STRING,
            Default="10.1.1.0/24"
        ))
        t.add_parameter(Parameter(
            "DmzSubnetCidrBlock3",
            Description="IP address range DMZ subnet 3. Default: 10.1.2.0/24",
            Type=constants.STRING,
            Default="10.1.2.0/24"
        ))
        t.add_parameter(Parameter(
            "BastionKeyPairName",
            Description="Name of an existing EC2 KeyPair to enable SSH "
                        "access to the backup instance",
            Type=constants.STRING,
        ))
        t.add_parameter(Parameter(
            "BastionImageId",
            Description="ID of an existing EC2 AMI image to use for "
                        "the backup instance",
            Type=constants.STRING,
        ))
        t.add_parameter(Parameter(
            "VirtualPrivateCloud",
            Description="The main VPC that the DMZ is to peer with",
            Type=constants.STRING
        ))
        t.add_parameter(Parameter(
            "VpcCidrBlock",
            Description="CIDR block of the VPC that the DMZ is to peer with",
            Type=constants.STRING
        ))
        t.add_parameter(Parameter(
            "VpcRouteTable",
            Description="Route table of the VPC that the DMZ is to peer with",
            Type=constants.STRING
        ))
        t.add_parameter(Parameter(
            "HostedZone",
            Description="Name of hosted zone to use for backup server",
            Type=constants.STRING
        ))
        t.add_parameter(Parameter(
            "SubDomain",
            Description="Name of custom subdomain to use for backup server",
            Type=constants.STRING
        ))
        t.add_parameter(Parameter(
            "UserData",
            Description="User Data to execute on backup server at deploy time",
            Type=constants.STRING
        ))

        """
        Deploy DMZ VPC
        """
        dmz_resource_name = Join(" ", [
            self._short_project,
            "DMZ for",
            Ref("DeploymentStage")
        ])
        server_name = Join("-", [
            self._file_project.replace('_', '-'),
            "backup-server",
            Ref("LowerStage")
        ])
        t.add_resource(VPC(
            "DemiliterizedZone",
            CidrBlock=Ref("DmzCidrBlock"),
            EnableDnsSupport=True,
            EnableDnsHostnames=True,
            Tags=Tags(Name=dmz_resource_name)
        ))
        t.add_resource(Subnet(
            "DmzSubnet1",
            VpcId=Ref("DemiliterizedZone"),
            CidrBlock=Ref("DmzSubnetCidrBlock1"),
            AvailabilityZone=Select('1', GetAZs('')),
            Tags=Tags(Name=Join(" ", ['PRIVATE', dmz_resource_name])),
            DependsOn=['DemiliterizedZone']
        ))
        t.add_resource(RouteTable(
            "DmzRouteTable",
            VpcId=Ref("DemiliterizedZone"),
            Tags=Tags(Name=Join(" ", ['PRIVATE', dmz_resource_name])),
            DependsOn=['DemiliterizedZone']
        ))

        t.add_resource(SubnetRouteTableAssociation(
            'DmzSubnetRouteTableAssociation',
            SubnetId=Ref('DmzSubnet1'),
            RouteTableId=Ref('DmzRouteTable'),
            DependsOn=['DmzRouteTable', 'DmzSubnet1']
        ))
        t.add_resource(Route(
            'DmzDefaultRoute',
            RouteTableId=Ref('DmzRouteTable'),
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=Ref('DmzInternetGateway'),
            DependsOn=['DmzRouteTable', 'DmzIGAttachment']
        ))

        t.add_resource(InternetGateway(
            "DmzInternetGateway",
            DependsOn=['DemiliterizedZone']
        ))
        t.add_resource(VPCGatewayAttachment(
            "DmzIGAttachment",
            VpcId=Ref("DemiliterizedZone"),
            InternetGatewayId=Ref("DmzInternetGateway"),
            DependsOn=['DemiliterizedZone', 'DmzInternetGateway']
        ))
        # The DMZ security group only allows SSH and HTTPS traffic
        # from the Internet and MySQL traffic between
        # the VPC and DMZ
        t.add_resource(SecurityGroup(
            "DMZSecurityGroup",
            GroupName=dmz_resource_name,
            GroupDescription=dmz_resource_name,
            VpcId=Ref("DemiliterizedZone"),
            Tags=Tags(Name=dmz_resource_name),
            SecurityGroupIngress=[
                SecurityGroupRule(
                    CidrIp="0.0.0.0/0",
                    IpProtocol="TCP",
                    FromPort='22',
                    ToPort='22',
                    Description=dmz_resource_name
                ),
                SecurityGroupRule(
                    CidrIp="0.0.0.0/0",
                    IpProtocol="TCP",
                    FromPort='443',
                    ToPort='443',
                    Description=dmz_resource_name
                ),
            ],
            SecurityGroupEgress=[
                SecurityGroupRule(
                    CidrIp=Ref("DmzCidrBlock"),
                    IpProtocol="TCP",
                    FromPort='3306',
                    ToPort='3306',
                    Description=dmz_resource_name
                ),
                SecurityGroupRule(
                    CidrIp=Ref("VpcCidrBlock"),
                    IpProtocol="TCP",
                    FromPort='3306',
                    ToPort='3306',
                    Description=dmz_resource_name
                ),
                SecurityGroupRule(
                    CidrIp="0.0.0.0/0",
                    IpProtocol="-1",
                    Description=dmz_resource_name
                ),
            ],
            DependsOn=['DemiliterizedZone']
        ))

        # An endpoint is how resources such as S3 connect
        # to the VPC to avoid data going over the Internet
        t.add_resource(VPCEndpoint(
            "DmzEndpointS3",
            VpcId=Ref("DemiliterizedZone"),
            ServiceName=Join(".", [
                "com",
                "amazonaws",
                Ref("AWS::Region"),
                "s3"
            ]),
            VpcEndpointType="Gateway",
            RouteTableIds=[Ref("DmzRouteTable")],
            DependsOn=['DemiliterizedZone', 'DmzRouteTable']
        ))
        t.add_resource(VPCEndpoint(
            "VPCEndpointSSM",
            VpcId=Ref("DemiliterizedZone"),
            ServiceName=Join(".", [
                "com",
                "amazonaws",
                Ref("AWS::Region"),
                "ssm"
            ]),
            VpcEndpointType="Interface",
            PrivateDnsEnabled=True,
            SecurityGroupIds=[Ref("DMZSecurityGroup")],
            SubnetIds=[Ref("DmzSubnet1")],
            DependsOn=['DemiliterizedZone', 'DMZSecurityGroup',
                       'DmzSubnet1']
        ))
        t.add_resource(VPCEndpoint(
            "VPCEndpointSSMMessages",
            VpcId=Ref("DemiliterizedZone"),
            ServiceName=Join(".", [
                "com",
                "amazonaws",
                Ref("AWS::Region"),
                "ssmmessages"
            ]),
            VpcEndpointType="Interface",
            PrivateDnsEnabled=True,
            SecurityGroupIds=[Ref("DMZSecurityGroup")],
            SubnetIds=[Ref("DmzSubnet1")],
            DependsOn=['DemiliterizedZone', 'DMZSecurityGroup',
                       'DmzSubnet1']
        ))
        t.add_resource(VPCEndpoint(
            "VPCEndpointEC2",
            VpcId=Ref("DemiliterizedZone"),
            ServiceName=Join(".", [
                "com",
                "amazonaws",
                Ref("AWS::Region"),
                "ec2"
            ]),
            VpcEndpointType="Interface",
            PrivateDnsEnabled=True,
            SecurityGroupIds=[Ref("DMZSecurityGroup")],
            SubnetIds=[Ref("DmzSubnet1")],
            DependsOn=['DemiliterizedZone', 'DMZSecurityGroup',
                       'DmzSubnet1']
        ))
        t.add_resource(VPCEndpoint(
            "VPCEndpointEC2Messages",
            VpcId=Ref("DemiliterizedZone"),
            ServiceName=Join(".", [
                "com",
                "amazonaws",
                Ref("AWS::Region"),
                "ec2messages"
            ]),
            VpcEndpointType="Interface",
            PrivateDnsEnabled=True,
            SecurityGroupIds=[Ref("DMZSecurityGroup")],
            SubnetIds=[Ref("DmzSubnet1")],
            DependsOn=['DemiliterizedZone', 'DMZSecurityGroup',
                       'DmzSubnet1']
        ))
        t.add_resource(VPCEndpoint(
            "VPCEndpointLogs",
            VpcId=Ref("DemiliterizedZone"),
            ServiceName=Join(".", [
                "com",
                "amazonaws",
                Ref("AWS::Region"),
                "logs"
            ]),
            VpcEndpointType="Interface",
            PrivateDnsEnabled=True,
            SecurityGroupIds=[Ref("DMZSecurityGroup")],
            SubnetIds=[Ref("DmzSubnet1")],
            DependsOn=['DemiliterizedZone', 'DMZSecurityGroup',
                       'DmzSubnet1']
        ))

        """
        Deploy Peering connection between DMZ and main VPC
        """
        t.add_resource(VPCPeeringConnection(
            "VPCPeeringConnection",
            VpcId=Ref("DemiliterizedZone"),
            PeerVpcId=Ref("VirtualPrivateCloud"),
            DependsOn=['DemiliterizedZone'],
            Tags=Tags(Name=dmz_resource_name),
        ))
        # Add routes to allow traffic between the peering VPCs
        t.add_resource(Route(
            'DmzPeeringRoute',
            DestinationCidrBlock=Ref('VpcCidrBlock'),
            RouteTableId=Ref('DmzRouteTable'),
            VpcPeeringConnectionId=Ref('VPCPeeringConnection'),
            DependsOn=['DmzRouteTable', 'VPCPeeringConnection']
        ))
        t.add_resource(Route(
            'VpcPeeringRoute',
            DestinationCidrBlock=Ref('DmzCidrBlock'),
            RouteTableId=Ref('VpcRouteTable'),
            VpcPeeringConnectionId=Ref('VPCPeeringConnection'),
            DependsOn=['VPCPeeringConnection']
        ))

        """
        Deploy Bastion Server
        """
        # Role to allow SSM
        t.add_resource(Role(
            "AccessSystemsManagerRole",
            RoleName=Join("-", [
                          self._dash_project,
                          Ref("LowerStage"),
                          "ec2-ssm-role"
                          ]),
            ManagedPolicyArns=[
                "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM",
                "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
            ],
            AssumeRolePolicyDocument=self._load_document(
                './policies/ec2_assume_role_policy.json'),
        ))
        t.add_resource(InstanceProfile(
            "SystemsManagerProfile",
            Roles=[Ref('AccessSystemsManagerRole')]
        ))
        # Bastion Server
        t.add_resource(Instance(
            "BastionInstance",
            ImageId=Ref("BastionImageId"),
            InstanceType="t2.micro",
            KeyName=Ref("BastionKeyPairName"),
            SecurityGroupIds=[Ref("DMZSecurityGroup")],
            SubnetId=Ref("DmzSubnet1"),
            IamInstanceProfile=Ref("SystemsManagerProfile"),
            UserData=Ref("UserData"),
            Tags=Tags(Name=server_name)
        ))
        # Bastion Elastic IP
        t.add_resource(EIP(
            "BastionElasticIP",
            InstanceId=Ref("BastionInstance"),
            Domain="vpc",
            DependsOn=["BastionInstance",
                       "DmzIGAttachment"]
        ))

        # Add DNS name
        ssh_domain_name = Join(".", [
            Ref("SubDomain"),
            Ref("HostedZone")
        ])
        t.add_resource(RecordSetGroup(
            "BastionRecord",
            HostedZoneName=Join("", [Ref("HostedZone"), "."]),
            RecordSets=[
                RecordSet(
                    Name=Join("", [ssh_domain_name, "."]),
                    Type="A",
                    TTL=300,
                    ResourceRecords=[Ref('BastionElasticIP')]
                )
            ],
            DependsOn=["BastionElasticIP"]
        ))

        """
        Output Bastion Server IP Address
        """
        t.add_output([
            Output(
                "BastionServerIpAddress",
                Description="IP address of backup server",
                Value=Ref('BastionElasticIP')
            ),
            Output(
                "BastionServerHostName",
                Description="Domain name of backup server",
                Value=ssh_domain_name
            ),
            Output(
                "BastionServerTagName",
                Description="Tagged name of backup server",
                Value=server_name
            ),
        ])

        """
        Create the template
        """
        return self._save_template(template_name, t.to_json())

    def _load_document(self, inpath):

        policy = None

        with open(inpath) as infile:
            policy = eval(infile.read())

        return policy

    def _save_template(self, name, outstr):

        outname = "{}_{}.{}".format(
            self._file_project,
            name,
            self._file_ext)

        with open(self._template_path + '/' + outname, 'w') as outfile:
            outfile.write(outstr)

        return outname
