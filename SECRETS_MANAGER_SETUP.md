# AWS Secrets Manager Setup Guide

This guide explains how to use AWS Secrets Manager for secure credential storage instead of Lambda environment variables.

## Why Use Secrets Manager?

✅ **More Secure**: Secrets are encrypted and not visible in Lambda console
✅ **Auditable**: CloudTrail logs all secret access
✅ **Rotatable**: Automatic secret rotation support
✅ **Fine-grained Access**: IAM policies control who can access secrets
✅ **Versioned**: Keep track of secret changes

❌ **Cost**: $0.40/month per secret + $0.05 per 10,000 API calls (typically < $1/month total)

## Setup Steps

### 1. Create the Secret

Create a single secret containing all your API keys:

```bash
aws secretsmanager create-secret \
  --name station95-chatbot/api-keys \
  --description "API keys for Station 95 GroupMe chatbot" \
  --secret-string '{
    "GROUPME_BOT_ID": "your-bot-id-here",
    "GROUPME_API_TOKEN": "your-groupme-token-here",
    "GROUPME_GROUP_ID": "your-group-id-here",
    "OPENAI_API_KEY": "sk-your-openai-key-here",
    "ANTHROPIC_API_KEY": ""
  }'
```

**Or** use a JSON file:

```bash
# Create secrets.json
cat > secrets.json <<EOF
{
  "GROUPME_BOT_ID": "your-bot-id-here",
  "GROUPME_API_TOKEN": "your-groupme-token-here",
  "GROUPME_GROUP_ID": "your-group-id-here",
  "OPENAI_API_KEY": "sk-your-openai-key-here",
  "ANTHROPIC_API_KEY": ""
}
EOF

# Create secret from file
aws secretsmanager create-secret \
  --name station95-chatbot/api-keys \
  --secret-string file://secrets.json

# Clean up (don't commit secrets.json!)
rm secrets.json
```

### 2. Deploy Lambda with Secrets Manager

**Using SAM** (recommended):

```bash
sam build
sam deploy \
  --parameter-overrides \
    UseSecretsManager=true \
    SecretsManagerSecretName=station95-chatbot/api-keys \
    AIProvider=openai \
    CalendarServiceUrl=https://your-calendar-service.com/commands
```

**Using CloudFormation**:

```bash
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name station95-chatbot-webhook \
  --parameter-overrides \
    UseSecretsManager=true \
    SecretsManagerSecretName=station95-chatbot/api-keys \
  --capabilities CAPABILITY_IAM
```

### 3. How It Works

```
┌─────────────────────────────────────────────────┐
│ Lambda Function Starts                          │
│  ↓                                              │
│ _get_secrets() called                          │
│  ↓                                              │
│ Check for SECRETS_MANAGER_SECRET_NAME          │
│  ↓                                              │
│ If set: Call Secrets Manager API               │
│  ↓                                              │
│ Cache secrets in memory (for warm starts)      │
│  ↓                                              │
│ Override environment variables with secrets    │
│  ↓                                              │
│ Pydantic Settings loads from env vars          │
│  ↓                                              │
│ Application uses settings.openai_api_key, etc. │
└─────────────────────────────────────────────────┘
```

## Local Development

For local testing with SAM, you have two options:

### Option 1: Use Environment Variables Locally

Create a `.env` file (DO NOT COMMIT):

```bash
# .env
GROUPME_BOT_ID=your-bot-id
GROUPME_API_TOKEN=your-token
GROUPME_GROUP_ID=your-group-id
OPENAI_API_KEY=sk-...
AI_PROVIDER=openai
CALENDAR_SERVICE_URL=http://localhost:8000/commands
```

Then run:

```bash
# SAM will use env vars instead of Secrets Manager
sam local start-api --env-vars .env
```

### Option 2: Use Real Secrets Manager Locally

If you have AWS credentials configured:

```bash
# SAM will call real Secrets Manager using your AWS profile
sam local start-api \
  --parameter-overrides UseSecretsManager=true \
  --aws-profile your-profile
```

**Note**: This will make real API calls to Secrets Manager (costs $0.05 per 10k calls).

## Managing Secrets

### View Secret (without revealing value)

```bash
aws secretsmanager describe-secret \
  --secret-id station95-chatbot/api-keys
```

### Update Secret

```bash
aws secretsmanager update-secret \
  --secret-id station95-chatbot/api-keys \
  --secret-string '{
    "GROUPME_BOT_ID": "new-value",
    "GROUPME_API_TOKEN": "new-token",
    "GROUPME_GROUP_ID": "group-id",
    "OPENAI_API_KEY": "sk-new-key",
    "ANTHROPIC_API_KEY": ""
  }'
```

**Note**: Lambda will automatically use the new values on the next cold start (or within seconds on warm containers due to caching).

### Update Single Key

```bash
# Get current secret
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id station95-chatbot/api-keys \
  --query SecretString --output text)

# Update just one key using jq
NEW=$(echo $CURRENT | jq '.OPENAI_API_KEY = "sk-new-key"')

# Save back
aws secretsmanager update-secret \
  --secret-id station95-chatbot/api-keys \
  --secret-string "$NEW"
```

### Rotate Secret

```bash
# Create new version (keeps old version for rollback)
aws secretsmanager put-secret-value \
  --secret-id station95-chatbot/api-keys \
  --secret-string file://new-secrets.json
```

### View Secret Value (be careful!)

```bash
# This will show the plaintext secret - don't run in production logs!
aws secretsmanager get-secret-value \
  --secret-id station95-chatbot/api-keys \
  --query SecretString --output text | jq .
```

## IAM Permissions

The Lambda function automatically gets these permissions when deployed:

```yaml
- Effect: Allow
  Action:
    - secretsmanager:GetSecretValue
  Resource: arn:aws:secretsmanager:region:account:secret:station95-chatbot/api-keys*
```

To allow a user/role to manage secrets:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:UpdateSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:station95-chatbot/api-keys*"
    }
  ]
}
```

## Cost Optimization

Secrets Manager costs:
- **Storage**: $0.40/month per secret
- **API calls**: $0.05 per 10,000 API calls

To minimize costs:

1. **Use caching** (already implemented): Lambda caches secrets in memory
2. **Combine secrets**: Store all keys in one secret (already done)
3. **Provisioned concurrency**: Reduces cold starts → fewer Secrets Manager calls

Typical monthly cost: **< $0.50** for low-traffic chatbot

## Troubleshooting

### Error: "Access Denied" when accessing secret

Check Lambda execution role has `secretsmanager:GetSecretValue` permission:

```bash
aws lambda get-function \
  --function-name station95-chatbot-webhook-webhook-handler \
  --query 'Configuration.Role'

# Check the role's policies
aws iam list-attached-role-policies --role-name your-lambda-role
```

### Secret not found

Verify secret exists and name matches:

```bash
aws secretsmanager list-secrets | grep station95-chatbot
```

### Lambda still using old values

Lambda caches secrets in memory. To force refresh:

1. Update the Lambda function (triggers cold start):
   ```bash
   aws lambda update-function-configuration \
     --function-name station95-chatbot-webhook-webhook-handler \
     --description "Force cold start"
   ```

2. Or wait ~15 minutes for warm containers to expire

### Local SAM can't access Secrets Manager

Ensure your AWS credentials are configured:

```bash
aws configure
# Or use:
export AWS_PROFILE=your-profile
```

## Fallback to Environment Variables

The Lambda is designed to gracefully fallback if Secrets Manager fails:

1. Tries to load from Secrets Manager
2. If fails (permission denied, secret not found, etc.), logs warning
3. Falls back to Lambda environment variables
4. Application continues to work

This makes it safe to deploy and test incrementally.

## Migration Guide

### From Environment Variables → Secrets Manager

1. **Create the secret** (Step 1 above)
2. **Redeploy with** `UseSecretsManager=true`
3. **Test** the webhook
4. **Remove old env vars** from template (optional cleanup)

### From Secrets Manager → Environment Variables

1. **Redeploy with** `UseSecretsManager=false` and provide env var values
2. **(Optional) Delete secret**:
   ```bash
   aws secretsmanager delete-secret \
     --secret-id station95-chatbot/api-keys \
     --force-delete-without-recovery  # Careful!
   ```

## Best Practices

✅ **DO**:
- Use Secrets Manager for production
- Use environment variables for local development
- Store all related secrets in one JSON object
- Enable CloudTrail to audit secret access
- Use IAM policies to restrict who can view secrets

❌ **DON'T**:
- Commit secrets to git (use `.env` with `.gitignore`)
- Log secret values
- Share secrets in chat/email
- Give broad `secretsmanager:*` permissions
