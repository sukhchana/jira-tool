"""
Architecture Design Prompt Templates

This module contains templates for generating various types of architecture diagrams
using the Mermaid diagramming syntax, specifically focused on AWS and GCP cloud architectures.
"""

from typing import Dict

# Base prompt template for generating an architecture overview
ARCHITECTURE_OVERVIEW_TEMPLATE = """
You are an expert solutions architect tasked with designing a cloud architecture for the following epic:

# Epic Title
{epic_title}

# Epic Description
{epic_description}

Given the requirements described in this epic, provide a comprehensive architecture overview.
Focus on explaining the high-level components and their interactions, the rationale behind
architectural decisions, and how the proposed solution addresses the key requirements.

Use {cloud_provider} as the primary cloud provider. The following services are approved for use:
{approved_services}

Additional context:
{additional_context}

Your overview should be detailed but concise, focusing on the architectural aspects rather than 
implementation details. Do not include actual Mermaid diagrams in this overview.
"""

# Templates for generating architecture diagrams specific to cloud providers
ARCHITECTURE_DIAGRAM_TEMPLATES = {
    "AWS": """
Generate a Mermaid architecture-beta diagram that visualizes the cloud architecture described in the epic.

# Epic Title
{epic_title}

# Epic Description
{epic_description}

Use AWS as the primary cloud provider. The following services are approved for use:
{approved_services}

Additional context:
{additional_context}

## AWS Architecture Diagram Guidelines

Create an architecture-beta diagram that clearly shows the components, their relationships, and the flow
of data. The diagram should use the following AWS service icons from the logos icon pack:

- Frontend/Public-facing services: aws-route53, aws-cloudfront, aws-s3, aws-apigateway, aws-appsync
- Compute: aws-lambda, aws-ec2, aws-eks, aws-ecs, aws-fargate, aws-elasticbeanstalk
- Data Storage: aws-dynamodb, aws-rds, aws-aurora, aws-s3, aws-elasticache, aws-redshift
- Messaging: aws-sqs, aws-sns, aws-eventbridge, aws-kinesis, aws-msk
- Security: aws-waf, aws-shield, aws-cognito, aws-iam, aws-secretsmanager
- Networking: aws-vpc, aws-cloudfront, aws-elb, aws-route53, aws-directconnect, aws-transitgateway
- Analytics: aws-athena, aws-emr, aws-quicksight, aws-glue
- Monitoring: aws-cloudwatch, aws-cloudtrail, aws-xray
- AI/ML: aws-sagemaker, aws-comprehend, aws-rekognition
- IoT: aws-iot, aws-iotanalytics, aws-iotevents
- Containers: aws-ecr, aws-ecs, aws-eks, aws-fargate
- Serverless: aws-lambda, aws-stepfunctions, aws-sam
- Storage: aws-s3, aws-efs, aws-fsx, aws-glacier, aws-snowball, aws-storagegateway
- Migration: aws-dms, aws-applicationmigrationservice, aws-servermigrationservice
- Management: aws-cloudformation, aws-opsworks, aws-servicecatalog, aws-systemsmanager

## Comprehensive AWS Service Icon Reference

```
# Compute Services
logos:aws-lambda - AWS Lambda
logos:aws-lambda-function - Lambda Function (alternative icon)
logos:aws-ec2 - EC2
logos:aws-ecs - ECS
logos:aws-eks - EKS 
logos:aws-elastic-beanstalk - Elastic Beanstalk
logos:aws-fargate - Fargate
logos:aws-app-runner - App Runner
logos:aws-batch - Batch
logos:aws-lightsail - Lightsail
logos:aws-outposts - Outposts

# Storage Services
logos:aws-s3 - S3 Storage
logos:aws-efs - Elastic File System
logos:aws-fsx - FSx
logos:aws-storage-gateway - Storage Gateway
logos:aws-backup - AWS Backup
logos:aws-snow-family - Snow Family
logos:aws-snowball - Snowball
logos:aws-snowcone - Snowcone
logos:aws-glacier - Glacier/S3 Glacier
logos:aws-s3-on-outposts - S3 on Outposts

# Database Services
logos:aws-dynamodb - DynamoDB
logos:aws-aurora - Aurora Database
logos:aws-rds - RDS
logos:aws-redshift - Redshift
logos:aws-neptune - Neptune
logos:aws-timestream - Timestream
logos:aws-documentdb - DocumentDB
logos:aws-elasticache - ElastiCache
logos:aws-keyspaces - Keyspaces
logos:aws-memorydb - MemoryDB
logos:aws-qldb - QLDB

# Networking Services
logos:aws-vpc - VPC
logos:aws-route53 - Route 53
logos:aws-cloudfront - CloudFront
logos:aws-elastic-load-balancing - ELB/Elastic Load Balancing
logos:aws-api-gateway - API Gateway
logos:aws-direct-connect - Direct Connect
logos:aws-transit-gateway - Transit Gateway
logos:aws-global-accelerator - Global Accelerator
logos:aws-cloud-map - Cloud Map
logos:aws-privatelink - PrivateLink
logos:aws-app-mesh - App Mesh
logos:aws-vpc-lattice - VPC Lattice
logos:aws-network-firewall - Network Firewall

# Messaging & Integration
logos:aws-sqs - SQS
logos:aws-sns - SNS
logos:aws-eventbridge - EventBridge
logos:aws-mq - MQ
logos:aws-step-functions - Step Functions
logos:aws-appsync - AppSync
logos:aws-kinesis - Kinesis

# Security, Identity & Compliance
logos:aws-iam - IAM
logos:aws-cognito - Cognito
logos:aws-kms - KMS
logos:aws-secrets-manager - Secrets Manager
logos:aws-certificate-manager - Certificate Manager (ACM)
logos:aws-waf - WAF
logos:aws-shield - Shield
logos:aws-firewall-manager - Firewall Manager
logos:aws-guardduty - GuardDuty
logos:aws-security-hub - Security Hub
logos:aws-inspector - Inspector
logos:aws-detective - Detective
logos:aws-artifact - Artifact
logos:aws-directory-service - Directory Service

# Management & Governance
logos:aws-cloudwatch - CloudWatch
logos:aws-cloudformation - CloudFormation
logos:aws-cloudtrail - CloudTrail
logos:aws-config - AWS Config
logos:aws-organization - Organizations
logos:aws-systems-manager - Systems Manager
logos:aws-control-tower - Control Tower
logos:aws-trusted-advisor - Trusted Advisor
logos:aws-health-dashboard - Health Dashboard
logos:aws-license-manager - License Manager

# Analytics & Machine Learning
logos:aws-emr - EMR
logos:aws-athena - Athena
logos:aws-glue - Glue
logos:aws-lake-formation - Lake Formation
logos:aws-sagemaker - SageMaker
logos:aws-opensearch - OpenSearch Service
logos:aws-quicksight - QuickSight

# Developer Tools
logos:aws-cloud9 - Cloud9
logos:aws-code-build - CodeBuild
logos:aws-code-commit - CodeCommit
logos:aws-code-deploy - CodeDeploy
logos:aws-code-pipeline - CodePipeline
logos:aws-cloud-development-kit - CDK
```

Make sure to use the architecture-beta diagram type with clear groups for logical separation.
For example:

```mermaid
architecture-beta
    group public(logos:aws-cloud)[Public Layer]
    group compute(logos:aws-lambda)[Compute Layer]
    group data(logos:aws-database)[Data Layer]
    group security[Security]

    service cdn(logos:aws-cloudfront)[CDN] in public
    service api(logos:aws-apigateway)[API Gateway] in public
    service lambda(logos:aws-lambda)[Lambda] in compute
    service dynamo(logos:aws-dynamodb)[DynamoDB] in data
    service cognito(logos:aws-cognito)[Cognito] in security

    cdn:B -- api:T
    api:B -- lambda:T
    lambda:B -- dynamo:T
    api:L -- cognito:R
```

For multi-regional architecture, you can organize by region:

```mermaid
architecture-beta
    group region1(logos:aws-cloud)[US East Region]
    group region2(logos:aws-cloud)[US West Region]
    
    group public1[Public Layer] in region1
    group compute1[Compute Layer] in region1
    group data1[Data Layer] in region1
    
    group public2[Public Layer] in region2
    group compute2[Compute Layer] in region2
    group data2[Data Layer] in region2
    
    service r53(logos:aws-route53)[Route 53]
    service cdn1(logos:aws-cloudfront)[CloudFront] in public1
    service alb1(logos:aws-elb)[ALB] in public1
    service ec21(logos:aws-ec2)[EC2 ASG] in compute1
    service rds1(logos:aws-rds)[Aurora Primary] in data1
    
    service cdn2(logos:aws-cloudfront)[CloudFront] in public2
    service alb2(logos:aws-elb)[ALB] in public2
    service ec22(logos:aws-ec2)[EC2 ASG] in compute2
    service rds2(logos:aws-rds)[Aurora Replica] in data2
    
    r53 -- cdn1
    r53 -- cdn2
    cdn1:B -- alb1:T
    cdn2:B -- alb2:T
    alb1:B -- ec21:T
    alb2:B -- ec22:T
    ec21:B -- rds1:T
    ec22:B -- rds2:T
    rds1:R -- rds2:L
```

## Complex AWS Example with Multiple Regions:

```mermaid
architecture-beta
    %% Define regions
    group usEast(logos:aws-general)[US East Region (Primary)]
        %% Network components
        service vpcEast(logos:aws-vpc)[VPC]
        service igwEast(logos:aws-internet-gateway)[Internet Gateway]
        service albEast(logos:aws-elastic-load-balancing)[Application Load Balancer]
        service natEast(logos:aws-nat-gateway)[NAT Gateway]
        service sgEast(logos:aws-security-group)[Security Group]
        
        %% Compute resources
        service ec2East(logos:aws-ec2)[Web Servers] in vpcEast
        service ecsEast(logos:aws-ecs)[Container Services] in vpcEast
        service lambdaEast(logos:aws-lambda)[Lambda Functions] in vpcEast
        
        %% Storage resources
        service s3East(logos:aws-s3)[Primary Storage]
        service efsEast(logos:aws-efs)[Shared File System] in vpcEast
        
        %% Database resources
        service rdsEast(logos:aws-aurora)[Primary Database] in vpcEast
        service ddbEast(logos:aws-dynamodb)[DynamoDB] in vpcEast
        service redisEast(logos:aws-elasticache)[ElastiCache] in vpcEast
        
        %% Connections within region
        igwEast:B -- T:vpcEast
        vpcEast:T -- B:albEast
        albEast:B -- T:ec2East
        ec2East:B -- T:ecsEast
        lambdaEast:L -- R:ecsEast
        natEast:R -- L:vpcEast
        sgEast:L -- R:ec2East
        
        ec2East:R -- L:efsEast
        ecsEast:B -- T:rdsEast
        lambdaEast:B -- T:ddbEast
        ec2East:L -- R:redisEast
        redisEast:B -- T:ddbEast
    end
    
    group usWest(logos:aws-general)[US West Region (DR)]
        %% Network components
        service vpcWest(logos:aws-vpc)[VPC] 
        service igwWest(logos:aws-internet-gateway)[Internet Gateway]
        service albWest(logos:aws-elastic-load-balancing)[Application Load Balancer]
        
        %% Compute resources
        service ec2West(logos:aws-ec2)[Web Servers] in vpcWest
        
        %% Storage resources
        service s3West(logos:aws-s3)[Backup Storage]
        
        %% Database resources
        service rdsWest(logos:aws-aurora)[Replica Database] in vpcWest
        
        %% Connections within region
        igwWest:B -- T:vpcWest
        vpcWest:T -- B:albWest
        albWest:B -- T:ec2West
        ec2West:B -- T:rdsWest
    end
    
    %% Cross-region connections
    rdsEast:R -- L:rdsWest
    s3East:R -- L:s3West
    
    %% Transit gateway for VPC connections
    service tgw(logos:aws-transit-gateway)[Transit Gateway]
    vpcEast:R -- L:tgw
    tgw:R -- L:vpcWest
    
    %% Global services
    service route53(logos:aws-route53)[Route 53]
    service cloudfront(logos:aws-cloudfront)[CloudFront]
    service shield(logos:aws-shield)[Shield]
    service waf(logos:aws-waf)[WAF]
    
    %% Connect global services
    route53:B -- T:albEast
    route53:B -- T:albWest
    cloudfront:L -- R:s3East
    shield:L -- R:route53
    waf:B -- T:cloudfront
    
    %% Monitoring and security
    service cloudwatch(logos:aws-cloudwatch)[CloudWatch]
    service cloudtrail(logos:aws-cloudtrail)[CloudTrail]
    service guardduty(logos:aws-guardduty)[GuardDuty]
    
    cloudwatch:T -- B:ec2East
    cloudtrail:T -- B:vpcEast
    guardduty:T -- B:vpcEast
```

Include service and resource names, use directional connections (T,B,L,R) for clear layout,
and group related services appropriately.
""",

    "GCP": """
Generate a Mermaid architecture-beta diagram that visualizes the cloud architecture described in the epic.

# Epic Title
{epic_title}

# Epic Description
{epic_description}

Use Google Cloud Platform (GCP) as the primary cloud provider. The following services are approved for use:
{approved_services}

Additional context:
{additional_context}

## GCP Architecture Diagram Guidelines

Create an architecture-beta diagram that clearly shows the components, their relationships, and the flow
of data. The diagram should use the following GCP service icons from the logos icon pack:

- Frontend/Public-facing services: gcp-loadbalancing, gcp-cdn, gcp-appengine, gcp-apigateway, firebase
- Compute: gcp-compute, gcp-functions, gcp-run, gcp-kubernetes, gcp-appengine
- Data Storage: gcp-sql, gcp-bigtable, gcp-datastore, gcp-firestore, gcp-spanner, gcp-storage, gcp-memorystore
- Messaging: gcp-pubsub, gcp-eventarc, gcp-tasks
- Security: gcp-iam, gcp-armor, gcp-iap, gcp-secretmanager
- Networking: gcp-vpn, gcp-cdn, gcp-interconnect, gcp-dns, gcp-loadbalancing, gcp-router
- Analytics: gcp-bigquery, gcp-dataflow, gcp-dataproc, gcp-looker
- Monitoring: gcp-monitoring, gcp-logging, gcp-trace
- AI/ML: gcp-ai, gcp-vision, gcp-speech, gcp-translate, gcp-vertex
- IoT: gcp-iot
- Containers: gcp-kubernetes, gcp-registry, gcp-run
- Serverless: gcp-functions, gcp-run, gcp-workflows
- Storage: gcp-storage, gcp-filestore, gcp-transfer
- Migration: gcp-transfer, gcp-migrationcenter
- Management: gcp-deployment, gcp-cloudscheduler, gcp-tasks

## Comprehensive GCP Service Icon Reference

```
# Compute Services
logos:gcp-compute - Compute Engine (GCE)
logos:gcp-functions - Cloud Functions
logos:gcp-run - Cloud Run
logos:gcp-kubernetes - GKE
logos:gcp-appengine - App Engine
logos:gcp-vmware - VMware Engine
logos:gcp-batch - Cloud Batch
logos:gcp-os-config - OS Config
logos:gcp-os-login - OS Login

# Storage Services
logos:gcp-storage - Cloud Storage
logos:gcp-filestore - Filestore
logos:gcp-persistent-disk - Persistent Disk
logos:gcp-transfer - Storage Transfer Service
logos:gcp-backup - Backup & DR Service
logos:gcp-storage-insights - Storage Insights

# Database Services
logos:gcp-firestore - Firestore
logos:gcp-sql - Cloud SQL
logos:gcp-spanner - Spanner
logos:gcp-bigtable - Bigtable
logos:gcp-memorystore - Memorystore
logos:gcp-datastore - Datastore
logos:gcp-database-migration - Database Migration Service
logos:gcp-alloydb - AlloyDB for PostgreSQL

# Networking Services
logos:gcp-loadbalancing - Load Balancing
logos:gcp-cdn - Cloud CDN
logos:gcp-dns - Cloud DNS
logos:gcp-interconnect - Cloud Interconnect
logos:gcp-network-connectivity - Network Connectivity Center
logos:gcp-network-intelligence - Network Intelligence Center
logos:gcp-nat - Cloud NAT
logos:gcp-network-service-tiers - Network Service Tiers
logos:gcp-private-service-connect - Private Service Connect
logos:gcp-router - Cloud Router
logos:gcp-service-directory - Service Directory
logos:gcp-vpn - Cloud VPN
logos:gcp-vpc - Virtual Private Cloud (VPC)

# API & Integration
logos:gcp-apigateway - API Gateway
logos:gcp-endpoints - Cloud Endpoints
logos:gcp-pubsub - Pub/Sub
logos:gcp-tasks - Cloud Tasks
logos:gcp-scheduler - Cloud Scheduler
logos:gcp-workflows - Workflows
logos:gcp-eventarc - Eventarc
logos:gcp-api-management - API Management
logos:gcp-apigee - Apigee API Platform
logos:gcp-integration-connectors - Integration Connectors

# Security & Identity
logos:gcp-iam - IAM
logos:gcp-kms - Key Management Service
logos:gcp-secretmanager - Secret Manager
logos:gcp-iap - Identity-Aware Proxy (IAP)
logos:gcp-armor - Cloud Armor
logos:gcp-certificate-manager - Certificate Manager
logos:gcp-security-command - Security Command Center
logos:gcp-dlp - Data Loss Prevention
logos:gcp-iam-admin - IAM Admin
logos:gcp-identity - Identity Platform
logos:gcp-binary-authorization - Binary Authorization
logos:gcp-access-context - Access Context Manager

# Management Tools
logos:gcp-logging - Cloud Logging
logos:gcp-monitoring - Cloud Monitoring
logos:gcp-trace - Cloud Trace
logos:gcp-deployment - Deployment Manager
logos:gcp-error-reporting - Error Reporting
logos:gcp-config-management - Config Management
logos:gcp-service-infrastructure - Service Infrastructure
logos:gcp-build - Cloud Build
logos:gcp-deploy - Cloud Deploy

# Analytics & ML
logos:gcp-bigquery - BigQuery
logos:gcp-dataflow - Dataflow
logos:gcp-vertex - Vertex AI
logos:gcp-data-catalog - Data Catalog
logos:gcp-dataproc - Dataproc
logos:gcp-data-fusion - Data Fusion
logos:gcp-bigquery-biengine - BigQuery BI Engine
logos:gcp-ai - AI Platform
logos:gcp-life-sciences - Life Sciences
logos:gcp-natural-language - Natural Language API
logos:gcp-speech - Speech-to-Text
logos:gcp-text-to-speech - Text-to-Speech
logos:gcp-translation - Translation API
logos:gcp-vision - Vision API

# Developer Tools
logos:gcp-cloud-code - Cloud Code
logos:gcp-cloud-tools - Cloud Tools for Eclipse
logos:gcp-cloud-shell - Cloud Shell
logos:gcp-source-repositories - Cloud Source Repositories
logos:gcp-artifact-registry - Artifact Registry
```

Make sure to use the architecture-beta diagram type with clear groups for logical separation.
For example:

```mermaid
architecture-beta
    group public(logos:gcp-cloud)[Public Layer]
    group compute(logos:gcp-compute)[Compute Layer]
    group data(logos:gcp-database)[Data Layer]
    group security[Security]

    service lb(logos:gcp-loadbalancing)[Load Balancer] in public
    service api(logos:gcp-apigateway)[API Gateway] in public
    service fun(logos:gcp-functions)[Cloud Functions] in compute
    service sql(logos:gcp-sql)[Cloud SQL] in data
    service iam(logos:gcp-iam)[IAM] in security

    lb:B -- api:T
    api:B -- fun:T
    fun:B -- sql:T
    api:L -- iam:R
```

For multi-regional architecture, you can organize by region:

```mermaid
architecture-beta
    group region1(logos:gcp-cloud)[US Central Region]
    group region2(logos:gcp-cloud)[Europe West Region]
    
    group public1[Public Layer] in region1
    group compute1[Compute Layer] in region1
    group data1[Data Layer] in region1
    
    group public2[Public Layer] in region2
    group compute2[Compute Layer] in region2
    group data2[Data Layer] in region2
    
    service dns(logos:gcp-dns)[Cloud DNS]
    service lb1(logos:gcp-loadbalancing)[Load Balancer] in public1
    service gke1(logos:gcp-kubernetes)[GKE] in compute1
    service sql1(logos:gcp-sql)[Cloud SQL Primary] in data1
    
    service lb2(logos:gcp-loadbalancing)[Load Balancer] in public2
    service gke2(logos:gcp-kubernetes)[GKE] in compute2
    service sql2(logos:gcp-sql)[Cloud SQL Replica] in data2
    
    dns -- lb1
    dns -- lb2
    lb1:B -- gke1:T
    lb2:B -- gke2:T
    gke1:B -- sql1:T
    gke2:B -- sql2:T
    sql1:R -- sql2:L
```

## Complex GCP Example with Multiple Regions:

```mermaid
architecture-beta
    %% Define regions
    group usCentral(logos:gcp-cloud)[US Central Region (Primary)]
        %% Network components
        service vpcCentral(logos:gcp-vpc)[VPC]
        service lbCentral(logos:gcp-loadbalancing)[Load Balancer]
        service fwCentral(logos:gcp-armor)[Cloud Armor]
        
        %% Compute resources
        service gkeCentral(logos:gcp-kubernetes)[GKE Cluster] in vpcCentral
        service runCentral(logos:gcp-run)[Cloud Run] in vpcCentral
        service functionsCentral(logos:gcp-functions)[Cloud Functions] in vpcCentral
        
        %% Storage resources
        service gscCentral(logos:gcp-storage)[Cloud Storage]
        service filestoreCentral(logos:gcp-filestore)[Filestore] in vpcCentral
        
        %% Database resources
        service sqlCentral(logos:gcp-sql)[Cloud SQL Primary] in vpcCentral
        service firestoreCentral(logos:gcp-firestore)[Firestore] in vpcCentral
        service redisCentral(logos:gcp-memorystore)[Memorystore] in vpcCentral
        
        %% Connections within region
        lbCentral:B -- T:vpcCentral
        fwCentral:R -- L:lbCentral
        lbCentral:B -- T:gkeCentral
        gkeCentral:R -- L:runCentral
        runCentral:R -- L:functionsCentral
        
        gkeCentral:B -- T:sqlCentral
        runCentral:B -- T:firestoreCentral
        functionsCentral:B -- T:gscCentral
        gkeCentral:R -- L:filestoreCentral
        gkeCentral:L -- R:redisCentral
    end
    
    group europeWest(logos:gcp-cloud)[Europe West Region (DR)]
        %% Network components
        service vpcEurope(logos:gcp-vpc)[VPC]
        service lbEurope(logos:gcp-loadbalancing)[Load Balancer]
        
        %% Compute resources
        service gkeEurope(logos:gcp-kubernetes)[GKE Cluster] in vpcEurope
        
        %% Storage resources
        service gscEurope(logos:gcp-storage)[Cloud Storage]
        
        %% Database resources
        service sqlEurope(logos:gcp-sql)[Cloud SQL Replica] in vpcEurope
        
        %% Connections within region
        lbEurope:B -- T:vpcEurope
        lbEurope:B -- T:gkeEurope
        gkeEurope:B -- T:sqlEurope
    end
    
    %% Cross-region connections
    sqlCentral:R -- L:sqlEurope
    gscCentral:R -- L:gscEurope
    
    %% Network Peering between VPCs
    service interconnect(logos:gcp-interconnect)[Cloud Interconnect]
    vpcCentral:R -- L:interconnect
    interconnect:R -- L:vpcEurope
    
    %% Global services
    service dns(logos:gcp-dns)[Cloud DNS]
    service cdn(logos:gcp-cdn)[Cloud CDN]
    
    %% Connect global services
    dns:B -- T:lbCentral
    dns:B -- T:lbEurope
    cdn:L -- R:gscCentral
    
    %% Monitoring and security
    service monitoring(logos:gcp-monitoring)[Cloud Monitoring]
    service logging(logos:gcp-logging)[Cloud Logging]
    service security(logos:gcp-security-command)[Security Command Center]
    
    monitoring:T -- B:gkeCentral
    logging:T -- B:vpcCentral
    security:T -- B:vpcCentral
```

Include service and resource names, use directional connections (T,B,L,R) for clear layout,
and group related services appropriately.
"""
}

# Template for generating sequence diagrams
SEQUENCE_DIAGRAM_TEMPLATE = """
Generate a Mermaid sequence diagram that illustrates the key interactions between components in the architecture.

# Epic Title
{epic_title}

# Epic Description
{epic_description}

Cloud Provider: {cloud_provider}
Approved Services: {approved_services}

Additional context:
{additional_context}

Create a sequence diagram that shows the flow of a critical user journey or system process. 
The diagram should:
1. Include all relevant components/services
2. Show the sequence of interactions with proper arrows
3. Include notes where helpful to explain complex steps
4. Focus on one key process (e.g., user authentication, data processing pipeline, etc.)

Example format:
```mermaid
sequenceDiagram
    participant User
    participant API as API Gateway
    participant Auth as Authentication Service
    participant DB as Database
    
    User->>API: Request resource
    API->>Auth: Validate token
    Auth->>DB: Check permissions
    DB-->>Auth: Return user permissions
    Auth-->>API: Token valid, permissions attached
    API->>DB: Query data
    DB-->>API: Return data
    API-->>User: Return resource
```

Choose the most important workflow to diagram based on the requirements in the epic.
"""

# Template for analyzing which diagrams would be most useful
DIAGRAM_ANALYSIS_TEMPLATE = """
Analyze the architecture requirements for the following epic and determine which diagram types 
would be most useful to include in addition to the architecture and sequence diagrams already provided.

# Epic Title
{epic_title}

# Epic Description
{epic_description}

Cloud Provider: {cloud_provider}
Approved Services: {approved_services}

Additional context:
{additional_context}

Based on these requirements, list the top 2-3 additional diagram types that would be most helpful 
for understanding this architecture, and explain why each would be valuable.

Choose from these diagram types:
1. Flowchart - For process flows, decision trees
2. Entity Relationship Diagram - For database schema relationships
3. Class Diagram - For service/component relationships and interfaces
4. State Diagram - For state transitions in the system
5. Gantt Chart - For implementation timelines
6. Pie Chart - For resource allocation visualization

For each recommended diagram type, briefly explain:
1. What aspect of the architecture it would clarify
2. Why this visualization would be valuable for understanding the solution

Format your response as a numbered list of diagram types with brief explanations.
"""

# Templates for specialized diagram types
DIAGRAM_TEMPLATES = {
    "flowchart": """
Generate a Mermaid flowchart diagram that visualizes a key process flow for the following epic:

# Epic Title
{epic_title}

# Epic Description
{epic_description}

Cloud Provider: {cloud_provider}
Approved Services: {approved_services}

Additional context:
{additional_context}

Create a flowchart that illustrates a critical process in this architecture. The flowchart should:
1. Have a clear starting point and endpoint
2. Include decision points with yes/no or conditional branches
3. Represent the logical flow of operations
4. Label each step clearly

Example format:
```mermaid
flowchart TD
    A[Start] --> B{User Authenticated?}
    B -->|Yes| C[Load User Dashboard]
    B -->|No| D[Redirect to Login]
    D --> E[Display Login Form]
    E --> F{Valid Credentials?}
    F -->|Yes| G[Generate JWT Token]
    F -->|No| H[Show Error Message]
    G --> C
    H --> E
    C --> I[End]
```

Choose the most critical process flow that would benefit from visualization.
""",

    "er": """
Generate a Mermaid Entity Relationship Diagram (ERD) for the data model in the following epic:

# Epic Title
{epic_title}

# Epic Description
{epic_description}

Cloud Provider: {cloud_provider}
Approved Services: {approved_services}

Additional context:
{additional_context}

Create an entity relationship diagram that illustrates the key data entities and their relationships. The ERD should:
1. Include all major entities/tables
2. Show relationships between entities (one-to-one, one-to-many, many-to-many)
3. List key attributes/fields for each entity
4. Use proper ER notation

Example format:
```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    CUSTOMER {
        string id PK
        string name
        string email
    }
    ORDER {
        string id PK
        string customer_id FK
        date created_at
        string status
    }
    LINE_ITEM {
        string id PK
        string order_id FK
        string product_id FK
        int quantity
        float price
    }
    PRODUCT {
        string id PK
        string name
        float price
        string description
    }
    LINE_ITEM }|--|| PRODUCT : references
```

Focus on the data model that would be most relevant for the requirements in the epic.
""",

    "class": """
Generate a Mermaid Class Diagram that illustrates the key components and their relationships for the following epic:

# Epic Title
{epic_title}

# Epic Description
{epic_description}

Cloud Provider: {cloud_provider}
Approved Services: {approved_services}

Additional context:
{additional_context}

Create a class diagram that shows the structure of the system components. The class diagram should:
1. Include the main services/components as classes
2. Show inheritance, composition, and association relationships
3. List key methods and properties for each class
4. Group related components logically

Example format:
```mermaid
classDiagram
    class AuthService {
        -userRepository
        +validateToken(token)
        +generateToken(user)
        +revokeToken(token)
    }
    
    class UserRepository {
        +findById(id)
        +save(user)
        +delete(id)
    }
    
    class User {
        -id
        -username
        -email
        -passwordHash
        +authenticate()
    }
    
    AuthService --> UserRepository : uses
    UserRepository --> User : manages
```

Focus on the key components and their relationships relevant to the epic requirements.
""",

    "state": """
Generate a Mermaid State Diagram that illustrates the state transitions for a key process in the following epic:

# Epic Title
{epic_title}

# Epic Description
{epic_description}

Cloud Provider: {cloud_provider}
Approved Services: {approved_services}

Additional context:
{additional_context}

Create a state diagram that shows how a critical element in the system changes states. The state diagram should:
1. Include all relevant states
2. Show transitions between states and what triggers them
3. Include any entry/exit actions for states
4. Highlight initial and final states

Example format:
```mermaid
stateDiagram-v2
    [*] --> Pending
    Pending --> Processing: Submit
    Processing --> Failed: Error Occurs
    Processing --> Succeeded: Process Complete
    Failed --> Processing: Retry
    Succeeded --> [*]
```

Choose the most important process or entity that undergoes state changes in this architecture.
""",

    "gantt": """
Generate a Mermaid Gantt Chart that outlines a high-level implementation timeline for the following epic:

# Epic Title
{epic_title}

# Epic Description
{epic_description}

Cloud Provider: {cloud_provider}
Approved Services: {approved_services}

Additional context:
{additional_context}

Create a Gantt chart that proposes an implementation timeline. The Gantt chart should:
1. Break down the implementation into logical phases
2. Include key milestones
3. Show dependencies between tasks
4. Include a realistic timeframe

Example format:
```mermaid
gantt
    title Implementation Timeline
    dateFormat  YYYY-MM-DD
    section Planning
    Requirements Analysis      :a1, 2023-01-01, 14d
    Architecture Design        :a2, after a1, 21d
    section Development
    Database Implementation    :b1, after a2, 14d
    Backend Development        :b2, after a2, 30d
    Frontend Development       :b3, after a2, 30d
    section Testing
    Integration Testing        :c1, after b1 b2 b3, 14d
    User Acceptance Testing    :c2, after c1, 14d
    section Deployment
    Production Deployment      :d1, after c2, 7d
    Post-Deployment Monitoring :d2, after d1, 14d
```

Create a reasonable implementation timeline based on the complexity described in the epic.
""",

    "pie": """
Generate a Mermaid Pie Chart that visualizes resource allocation or distribution for the following epic:

# Epic Title
{epic_title}

# Epic Description
{epic_description}

Cloud Provider: {cloud_provider}
Approved Services: {approved_services}

Additional context:
{additional_context}

Create a pie chart that illustrates an important distribution aspect of this architecture. The pie chart could show:
1. Resource allocation across services
2. Cost distribution
3. Traffic patterns
4. Storage distribution
5. Any other meaningful proportion that helps understand the architecture

Example format:
```mermaid
pie
    title Resource Allocation
    "Compute" : 40
    "Storage" : 25
    "Database" : 20
    "Networking" : 10
    "Monitoring" : 5
```

Choose the most relevant distribution to visualize based on the requirements in the epic.
"""
}

# Function to get the appropriate architecture diagram template based on cloud provider
def get_architecture_diagram_template(cloud_provider: str) -> str:
    """Get the architecture diagram template for the specified cloud provider."""
    cloud_provider = cloud_provider.upper()
    if cloud_provider in ARCHITECTURE_DIAGRAM_TEMPLATES:
        return ARCHITECTURE_DIAGRAM_TEMPLATES[cloud_provider]
    return ARCHITECTURE_DIAGRAM_TEMPLATES["AWS"]  # Default to AWS if provider not found 