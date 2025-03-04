"""
Configuration file containing lists of approved cloud services for architecture designs.
"""

# Approved AWS Services
AWS_APPROVED_SERVICES = [
    # Compute
    "EC2", "Lambda", "ECS", "EKS", "Fargate", "Batch", "Lightsail",
    
    # Storage
    "S3", "EBS", "EFS", "FSx", "Storage Gateway",
    
    # Database
    "RDS", "DynamoDB", "ElastiCache", "Neptune", "Redshift", "DocumentDB", "QLDB", "Keyspaces", "Timestream",
    
    # Networking & Content Delivery
    "VPC", "CloudFront", "Route 53", "API Gateway", "Direct Connect", "Transit Gateway", "App Mesh", "Global Accelerator",
    
    # Security, Identity & Compliance
    "IAM", "Cognito", "Secrets Manager", "GuardDuty", "Inspector", "CloudTrail", "Shield", "WAF", "KMS", "Certificate Manager",
    
    # Analytics
    "Athena", "EMR", "CloudSearch", "Elasticsearch Service", "Kinesis", "QuickSight", "Data Pipeline", "Glue", "Lake Formation",
    
    # Integration
    "SQS", "SNS", "EventBridge", "MQ", "SES", "Step Functions",
    
    # Management & Governance
    "CloudWatch", "CloudFormation", "Systems Manager", "Control Tower", "Config", "OpsWorks", "Service Catalog", "Trusted Advisor",
    
    # Containers
    "ECR", "ECS", "EKS", "App Runner",
    
    # Developer Tools
    "CodeCommit", "CodeBuild", "CodeDeploy", "CodePipeline", "CodeStar", "Cloud9", "X-Ray",
    
    # Machine Learning
    "SageMaker", "Comprehend", "Translate", "Rekognition", "Polly", "Lex", "Personalize"
]

# Approved GCP Services
GCP_APPROVED_SERVICES = [
    # Compute
    "Compute Engine", "App Engine", "Google Kubernetes Engine (GKE)", "Cloud Run", "Cloud Functions",
    
    # Storage
    "Cloud Storage", "Persistent Disk", "Filestore",
    
    # Database
    "Cloud SQL", "Cloud Spanner", "Firestore", "Cloud Bigtable", "Memorystore", "Cloud Datastore",
    
    # Networking
    "Virtual Private Cloud (VPC)", "Cloud Load Balancing", "Cloud CDN", "Cloud DNS", "Cloud Interconnect", "Cloud VPN",
    
    # Security & Identity
    "Cloud IAM", "Cloud Identity", "Resource Manager", "Secret Manager", "Cloud KMS", "Security Command Center",
    
    # Big Data
    "BigQuery", "Dataflow", "Dataproc", "Pub/Sub", "Data Fusion", "Cloud Composer", "Cloud Data Catalog",
    
    # AI & Machine Learning
    "Vertex AI", "Vision AI", "Natural Language AI", "Translation AI", "Speech-to-Text", "Text-to-Speech", "Dialogflow",
    
    # Management Tools
    "Cloud Monitoring", "Cloud Logging", "Cloud Trace", "Cloud Deployment Manager", "Cloud Endpoints",
    
    # Developer Tools
    "Cloud Build", "Cloud Source Repositories", "Container Registry", "Artifact Registry", "Cloud Scheduler",
    
    # Migration
    "Transfer Service", "Database Migration Service", "Migrate for Compute Engine",
    
    # API Management
    "API Gateway", "Apigee API Management"
] 