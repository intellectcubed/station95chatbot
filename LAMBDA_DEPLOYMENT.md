# Lambda Deployment Guide

This guide explains how to deploy the GroupMe webhook handler as an AWS Lambda function with API Gateway.

## Architecture Overview

The deployment consists of:

- **AWS Lambda**: Runs the webhook handler code (`groupme_webhook_handler_lambda.py`)
- **API Gateway HTTP API**: Receives webhook calls from GroupMe and forwards to Lambda
- **IAM Role**: Grants Lambda permissions to execute and write logs
- **CloudWatch Logs**: Stores Lambda execution logs
- **S3 Bucket**: Stores message processing logs (optional)

## Prerequisites

1. **AWS Account** with appropriate permissions to create:
   - Lambda functions
   - API Gateway APIs
   - IAM roles
   - S3 buckets
   - CloudWatch log groups
   - Secrets Manager secrets (recommended for production)

2. **AWS CLI** installed and configured:
   ```bash
   aws configure
   ```

3. **Credentials Setup** - Choose one:

   **Option A: Secrets Manager (Recommended for Production)**

   See [SECRETS_MANAGER_SETUP.md](SECRETS_MANAGER_SETUP.md) for detailed guide.

   ```bash
   # Create secret with all API keys
   aws secretsmanager create-secret \
     --name station95-chatbot/api-keys \
     --secret-string '{
       "GROUPME_BOT_ID": "your-bot-id",
       "GROUPME_API_TOKEN": "your-api-token",
       "GROUPME_GROUP_ID": "your-group-id",
       "OPENAI_API_KEY": "sk-your-key"
     }'
   ```

   **Option B: Environment Variables (Simpler for Testing)**

   ```bash
   export GROUPME_BOT_ID="your-bot-id"
   export GROUPME_API_TOKEN="your-api-token"
   export GROUPME_GROUP_ID="your-group-id"
   export OPENAI_API_KEY="your-openai-key"  # or ANTHROPIC_API_KEY
   export AI_PROVIDER="openai"  # or "anthropic"
   export CALENDAR_SERVICE_URL="your-calendar-service-url"
   ```

4. **Python Dependencies** installed locally:
   ```bash
   pip install -r requirements.txt
   ```

## Deployment Options

### Option 1: Quick Deploy (Recommended)

Use the provided deployment script:

```bash
./deploy-lambda.sh
```

This script will:
1. Create an S3 bucket for Lambda code
2. Package your code and dependencies
3. Upload to S3
4. Deploy the CloudFormation stack
5. Output the webhook URL

### Option 2: Manual CloudFormation Deploy

1. **Package the Lambda code:**
   ```bash
   # Create package directory
   mkdir -p lambda-package

   # Install dependencies
   pip install -r requirements.txt -t lambda-package/

   # Copy source code
   cp -r src/station95chatbot lambda-package/
   cp groupme_webhook_handler_lambda.py lambda-package/
   cp -r data lambda-package/  # If you have a data directory

   # Create ZIP
   cd lambda-package
   zip -r ../lambda-deployment-package.zip .
   cd ..
   ```

2. **Create S3 bucket and upload:**
   ```bash
   aws s3 mb s3://your-bucket-name
   aws s3 cp lambda-deployment-package.zip s3://your-bucket-name/
   ```

3. **Update CloudFormation template:**

   Edit `cloudformation-template.yaml` and replace the `Code` section in `GroupMeWebhookLambda` resource:
   ```yaml
   Code:
     S3Bucket: your-bucket-name
     S3Key: lambda-deployment-package.zip
   ```

4. **Deploy stack:**
   ```bash
   aws cloudformation deploy \
     --template-file cloudformation-template.yaml \
     --stack-name station95-chatbot-webhook \
     --parameter-overrides \
       GroupMeBotId=$GROUPME_BOT_ID \
       GroupMeApiToken=$GROUPME_API_TOKEN \
       GroupMeGroupId=$GROUPME_GROUP_ID \
       AIProvider=$AI_PROVIDER \
       OpenAIApiKey=$OPENAI_API_KEY \
       CalendarServiceUrl=$CALENDAR_SERVICE_URL \
     --capabilities CAPABILITY_NAMED_IAM
   ```

### Option 3: AWS SAM Deploy (Alternative)

If you prefer AWS SAM (Serverless Application Model):

1. **Install AWS SAM CLI:**
   ```bash
   # macOS
   brew install aws-sam-cli

   # Or download from: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
   ```

2. **Create `samconfig.toml`** (see file in repository)

3. **Deploy:**
   ```bash
   sam build
   sam deploy --guided
   ```

## Post-Deployment

### 1. Get the Webhook URL

After deployment, get your webhook URL:

```bash
aws cloudformation describe-stacks \
  --stack-name station95-chatbot-webhook \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
  --output text
```

### 2. Configure GroupMe Bot

Update your GroupMe bot's callback URL:

```bash
curl -X POST https://api.groupme.com/v3/bots/update \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": "YOUR_BOT_ID",
    "callback_url": "YOUR_WEBHOOK_URL"
  }'
```

Or use the GroupMe developer portal: https://dev.groupme.com/bots

### 3. Test the Deployment

**Health check:**
```bash
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/health
```

**Send test webhook:**
```bash
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test123",
    "name": "Test User",
    "text": "Test message",
    "sender_type": "user",
    "created_at": 1234567890,
    "group_id": "test-group",
    "sender_id": "test-sender",
    "system": false
  }'
```

### 4. Monitor Logs

**View Lambda logs:**
```bash
# Tail logs in real-time
aws logs tail /aws/lambda/station95-chatbot-webhook-webhook-handler --follow

# View recent logs
aws logs tail /aws/lambda/station95-chatbot-webhook-webhook-handler --since 1h
```

**View API Gateway logs:**
```bash
aws logs tail /aws/apigateway/station95-chatbot-webhook-http-api --follow
```

## Updating the Lambda

After making code changes:

1. **Re-run the deployment script:**
   ```bash
   ./deploy-lambda.sh
   ```

Or manually:

2. **Package and upload new code:**
   ```bash
   # ... (same packaging steps as above)
   aws s3 cp lambda-deployment-package.zip s3://your-bucket-name/
   ```

3. **Update Lambda function:**
   ```bash
   aws lambda update-function-code \
     --function-name station95-chatbot-webhook-webhook-handler \
     --s3-bucket your-bucket-name \
     --s3-key lambda-deployment-package.zip
   ```

## Troubleshooting

### Lambda Timeout Errors

If you see timeout errors, increase the Lambda timeout:

```bash
aws lambda update-function-configuration \
  --function-name station95-chatbot-webhook-webhook-handler \
  --timeout 60
```

Or update the CloudFormation template `Timeout` parameter.

### Environment Variable Issues

Check Lambda environment variables:

```bash
aws lambda get-function-configuration \
  --function-name station95-chatbot-webhook-webhook-handler \
  --query 'Environment.Variables'
```

Update environment variables:

```bash
aws lambda update-function-configuration \
  --function-name station95-chatbot-webhook-webhook-handler \
  --environment Variables="{GROUPME_BOT_ID=new-value,...}"
```

### Permission Errors

Ensure the Lambda execution role has necessary permissions. Check the CloudFormation template's `LambdaExecutionRole` resource.

### Cold Start Performance

Lambda functions have "cold starts" when not recently invoked. To reduce latency:

1. **Increase memory** (more CPU allocated):
   ```yaml
   MemorySize: 1024  # Increase from 512
   ```

2. **Use Provisioned Concurrency** (costs more):
   ```bash
   aws lambda put-provisioned-concurrency-config \
     --function-name station95-chatbot-webhook-webhook-handler \
     --provisioned-concurrent-executions 1
   ```

## Cost Estimation

Approximate monthly costs (may vary by region):

- **Lambda**:
  - Free tier: 1M requests/month, 400,000 GB-seconds
  - After: $0.20 per 1M requests + $0.0000166667 per GB-second

- **API Gateway HTTP API**:
  - $1.00 per million requests

- **CloudWatch Logs**:
  - $0.50 per GB ingested
  - $0.03 per GB stored

- **S3**:
  - $0.023 per GB stored
  - Minimal for log storage

**Estimated cost for low-volume usage**: < $1/month

## Cleanup

To delete all resources:

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name station95-chatbot-webhook

# Delete S3 bucket (after emptying it)
aws s3 rb s3://your-bucket-name --force

# Delete log groups
aws logs delete-log-group --log-group-name /aws/lambda/station95-chatbot-webhook-webhook-handler
aws logs delete-log-group --log-group-name /aws/apigateway/station95-chatbot-webhook-http-api
```

## Additional Resources

- [AWS Lambda Python Documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [API Gateway HTTP API Documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [GroupMe Bot API Documentation](https://dev.groupme.com/docs/v3)
- [CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
