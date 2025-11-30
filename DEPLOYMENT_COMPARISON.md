# Deployment Options Comparison

Quick reference guide for choosing the right deployment method for your needs.

## Credentials Storage

### AWS Secrets Manager vs Environment Variables

| Aspect | Secrets Manager ✅ | Environment Variables |
|--------|-------------------|----------------------|
| **Security** | High - encrypted, not visible in console | Low - visible to anyone with Lambda access |
| **Rotation** | Automatic rotation support | Manual only |
| **Audit Trail** | CloudTrail logs all access | No audit trail |
| **Access Control** | Fine-grained IAM policies | All-or-nothing Lambda access |
| **Cost** | ~$0.50/month | Free |
| **Setup Complexity** | Medium | Simple |
| **Local Testing** | Works with SAM + AWS credentials | Easy with `.env` files |
| **Best For** | **Production** | Development/testing |

**Recommendation**: Use **Secrets Manager for production**, environment variables for local development.

---

## Deployment Tools

### SAM vs CloudFormation vs Deploy Script

| Feature | AWS SAM | Pure CloudFormation | Deploy Script |
|---------|---------|-------------------|--------------|
| **Template File** | `template.yaml` | `cloudformation-template.yaml` | Uses CloudFormation |
| **Lines of Code** | ~170 | ~250+ | N/A |
| **Deploy Command** | `sam deploy` | `aws cloudformation deploy` | `./deploy-lambda.sh` |
| **Local Testing** | ✅ `sam local start-api` | ❌ Not supported | ❌ Not supported |
| **Packaging** | Automatic | Manual | Automated by script |
| **Prerequisites** | SAM CLI | AWS CLI only | AWS CLI + bash |
| **Learning Curve** | Gentle | Steeper | Simplest |
| **Flexibility** | Medium | High | Medium |
| **Best For** | **Most users** | Complex customization | One-command deploy |

**Recommendation**: Start with **SAM** for easiest experience.

---

## Quick Decision Matrix

### Choose Your Deployment Strategy:

```
Are you deploying to production?
  ├─ YES → Use Secrets Manager + SAM
  │        Commands:
  │        1. aws secretsmanager create-secret --name station95-chatbot/api-keys --secret-string '{...}'
  │        2. sam build && sam deploy --parameter-overrides UseSecretsManager=true
  │
  └─ NO (Testing/Development)
       ├─ Want local testing? → Use SAM + .env file
       │                         Commands:
       │                         1. Create .env file with keys
       │                         2. sam build && sam local start-api
       │
       └─ Just want it deployed fast? → Use deploy script + env vars
                                         Commands:
                                         1. export GROUPME_BOT_ID=...
                                         2. ./deploy-lambda.sh
```

---

## Common Scenarios

### Scenario 1: First Time Setup (Learning)

**Use**: Deploy script + Environment variables

```bash
export GROUPME_BOT_ID="..."
export GROUPME_API_TOKEN="..."
export GROUPME_GROUP_ID="..."
export OPENAI_API_KEY="sk-..."

./deploy-lambda.sh
```

**Why**: Simplest path to get something working.

---

### Scenario 2: Local Development

**Use**: SAM + .env file

```bash
# Create .env file
cat > .env <<EOF
GROUPME_BOT_ID=...
OPENAI_API_KEY=sk-...
EOF

# Run locally
sam build
sam local start-api --env-vars .env

# Test locally
curl http://localhost:3000/health
```

**Why**: Test changes without deploying to AWS.

---

### Scenario 3: Production Deployment

**Use**: SAM + Secrets Manager

```bash
# One-time: Create secret
aws secretsmanager create-secret \
  --name station95-chatbot/api-keys \
  --secret-string file://secrets.json

# Deploy
sam build
sam deploy \
  --parameter-overrides \
    UseSecretsManager=true \
    AIProvider=openai \
    CalendarServiceUrl=https://your-service.com/commands
```

**Why**: Most secure, professional setup.

---

### Scenario 4: Multiple Environments (Dev/Staging/Prod)

**Use**: SAM with parameter files

```bash
# Create samconfig-dev.toml
[dev.deploy.parameters]
stack_name = "station95-dev"
parameter_overrides = "UseSecretsManager=false GroupMeBotId=dev-bot ..."

# Create samconfig-prod.toml
[prod.deploy.parameters]
stack_name = "station95-prod"
parameter_overrides = "UseSecretsManager=true SecretsManagerSecretName=station95-prod/api-keys"

# Deploy to dev
sam deploy --config-env dev

# Deploy to prod
sam deploy --config-env prod
```

**Why**: Manage multiple environments easily.

---

### Scenario 5: CI/CD Pipeline

**Use**: SAM with GitHub Actions / AWS CodePipeline

```yaml
# .github/workflows/deploy.yml
- name: SAM Build
  run: sam build

- name: SAM Deploy
  run: sam deploy --no-confirm-changeset --no-fail-on-empty-changeset
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

**Why**: Automated, repeatable deployments.

---

## Cost Comparison

### Minimal Traffic (< 1000 requests/month)

| Component | Secrets Manager | Env Variables |
|-----------|----------------|---------------|
| Lambda | Free tier | Free tier |
| API Gateway | Free tier | Free tier |
| Secrets Manager | $0.40/month | $0 |
| CloudWatch Logs | ~$0.10 | ~$0.10 |
| **Total** | **~$0.50/month** | **~$0.10/month** |

### Medium Traffic (10,000 requests/month)

| Component | Secrets Manager | Env Variables |
|-----------|----------------|---------------|
| Lambda | ~$0.20 | ~$0.20 |
| API Gateway | ~$0.01 | ~$0.01 |
| Secrets Manager | $0.41 | $0 |
| CloudWatch Logs | ~$0.50 | ~$0.50 |
| **Total** | **~$1.12/month** | **~$0.71/month** |

**Note**: Security is worth $0.40/month in production! 🔒

---

## Migration Paths

### From Deploy Script → SAM

```bash
# Your current CloudFormation stack exists
# SAM can take over:

sam build
sam deploy \
  --stack-name station95-chatbot-webhook \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM
```

### From Environment Variables → Secrets Manager

```bash
# 1. Get current env vars from Lambda
aws lambda get-function-configuration \
  --function-name station95-chatbot-webhook-webhook-handler \
  --query 'Environment.Variables' > current-config.json

# 2. Create secret from current config
aws secretsmanager create-secret \
  --name station95-chatbot/api-keys \
  --secret-string file://current-config.json

# 3. Redeploy with Secrets Manager enabled
sam deploy --parameter-overrides UseSecretsManager=true
```

---

## Troubleshooting Decision Tree

```
Deployment failed?
  ├─ "Access Denied" → Check IAM permissions
  ├─ "Secret not found" → Create secret first (see SECRETS_MANAGER_SETUP.md)
  ├─ "Template validation error" → Check YAML syntax
  └─ "Function timeout" → Increase Lambda timeout

Lambda not working?
  ├─ Check CloudWatch Logs: aws logs tail /aws/lambda/...
  ├─ Test health endpoint: curl https://your-api/health
  └─ Check environment variables: aws lambda get-function-configuration

Local SAM not working?
  ├─ "Cannot find credentials" → Run: aws configure
  ├─ Port already in use → Use: sam local start-api --port 3001
  └─ Dependencies missing → Run: sam build
```

---

## Summary Recommendations

| Situation | Use This |
|-----------|----------|
| 🚀 Just getting started | Deploy script + env vars |
| 💻 Developing locally | SAM + .env file |
| 🏢 Production deployment | SAM + Secrets Manager |
| 🔧 Need maximum control | Pure CloudFormation |
| 🔄 CI/CD pipeline | SAM with GitHub Actions |
| 💰 Minimal cost | Env variables (but less secure) |
| 🔒 Maximum security | Secrets Manager |

**Most Common Path**:
1. Start with deploy script for learning
2. Switch to SAM for development
3. Add Secrets Manager for production
