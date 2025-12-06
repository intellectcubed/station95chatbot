# API Gateway Security Guide

This guide covers how to restrict access to your webhook endpoint so only you and GroupMe can access it.

## The Problem

By default, your API Gateway endpoint is **publicly accessible**. Anyone who discovers your URL could:
- Send fake webhook requests
- Spam your Lambda function (costs money)
- Attempt to exploit vulnerabilities

## Security Options

### ✅ Option 1: Secret URL Path (RECOMMENDED)

**How it works**: Instead of `/webhook`, use `/webhook/{random-secret}`. Only you and GroupMe know the secret.

**Pros**:
- Simple to implement
- No additional AWS costs
- Works perfectly with GroupMe
- Easy to rotate the secret

**Cons**:
- If the URL leaks, attackers can access it
- Not as strong as cryptographic verification

#### Setup:

```bash
# Generate a random secret (32 characters recommended)
SECRET=$(openssl rand -hex 16)
echo "Your webhook secret: $SECRET"

# Deploy with the secret
sam deploy \
  --parameter-overrides \
    WebhookSecret=$SECRET \
    UseSecretsManager=true
```

#### Your webhook URL will be:
```
https://your-api-id.execute-api.us-east-1.amazonaws.com/webhook/abc123xyz456...
```

#### Configure GroupMe:
```bash
curl -X POST https://api.groupme.com/v3/bots/update \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": "YOUR_BOT_ID",
    "callback_url": "https://your-api-id.../webhook/abc123xyz456..."
  }'
```

#### Rotate the secret:
```bash
# Generate new secret
NEW_SECRET=$(openssl rand -hex 16)

# Redeploy with new secret
sam deploy --parameter-overrides WebhookSecret=$NEW_SECRET

# Update GroupMe with new URL
curl -X POST https://api.groupme.com/v3/bots/update ...
```

---

### ✅ Option 2: Request Validation (Layer 2)

**How it works**: Validate that incoming requests look like legitimate GroupMe webhooks.

**Pros**: Free, catches malformed requests
**Cons**: Smart attackers can forge valid-looking requests

#### Implementation:

Update `groupme_webhook_handler_lambda.py` to add validation:

```python
def _validate_groupme_request(data: dict) -> bool:
    """Validate that the request looks like a GroupMe webhook."""
    required_fields = ["id", "name", "text", "sender_type", "created_at", "group_id"]

    # Check required fields exist
    if not all(field in data for field in required_fields):
        logger.warning(f"Missing required fields: {data.keys()}")
        return False

    # Check group_id matches your group
    expected_group_id = os.environ.get("GROUPME_GROUP_ID")
    if data.get("group_id") != expected_group_id:
        logger.warning(f"Invalid group_id: {data.get('group_id')}")
        return False

    # Check timestamp is recent (within last 5 minutes)
    import time
    current_time = int(time.time())
    message_time = data.get("created_at", 0)
    if abs(current_time - message_time) > 300:  # 5 minutes
        logger.warning(f"Timestamp too old: {message_time}")
        return False

    return True

# In _handle_webhook, add validation:
async def _handle_webhook(data: dict[str, Any]) -> dict[str, Any]:
    logger.info(f"Received webhook: {json.dumps(data)}")

    # Validate request
    if not _validate_groupme_request(data):
        logger.error("Invalid webhook request")
        return {"status": "error", "message": "Invalid request"}

    # ... rest of existing code
```

---

### ✅ Option 3: IP Whitelist with WAF (Most Secure, Costs Extra)

**How it works**: Use AWS WAF to only allow requests from GroupMe's IP addresses and your IP.

**Pros**: Very secure, blocks at network level
**Cons**:
- Costs ~$5-10/month
- GroupMe may change IPs without notice
- Your IP might change (if not static)

#### Setup:

1. **Find GroupMe's IP ranges** (contact GroupMe support or monitor logs)

2. **Create WAF Web ACL**:

```bash
# Get your current IP
MY_IP=$(curl -s ifconfig.me)

# Create WAF (adds ~$5/month)
aws wafv2 create-web-acl \
  --name station95-webhook-waf \
  --scope REGIONAL \
  --default-action Block={} \
  --rules file://waf-rules.json
```

**waf-rules.json**:
```json
[
  {
    "Name": "AllowMyIP",
    "Priority": 1,
    "Statement": {
      "IPSetReferenceStatement": {
        "Arn": "arn:aws:wafv2:us-east-1:ACCOUNT:regional/ipset/my-ips/..."
      }
    },
    "Action": {"Allow": {}},
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "AllowMyIP"
    }
  },
  {
    "Name": "AllowGroupMe",
    "Priority": 2,
    "Statement": {
      "IPSetReferenceStatement": {
        "Arn": "arn:aws:wafv2:us-east-1:ACCOUNT:regional/ipset/groupme-ips/..."
      }
    },
    "Action": {"Allow": {}},
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "AllowGroupMe"
    }
  }
]
```

3. **Associate WAF with API Gateway**:
```bash
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:... \
  --resource-arn arn:aws:apigateway:...
```

**Warning**: GroupMe doesn't publish their IP ranges. You'd need to:
- Monitor CloudWatch logs to identify GroupMe's IPs
- Keep the list updated
- Risk blocking legitimate traffic if they change IPs

---

### ✅ Option 4: API Gateway Resource Policy (IP Whitelist)

**How it works**: Use API Gateway resource policy to restrict by IP (free, simpler than WAF).

**Pros**: Free, easier than WAF
**Cons**: Same IP change issues as WAF

Add to `template.yaml`:

```yaml
Resources:
  HttpApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: !Sub '${AWS::StackName}-http-api'
      ProtocolType: HTTP
      # Note: HTTP APIs don't support resource policies
      # Use REST API instead:

  # Change to REST API for resource policy support
  RestApi:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: !Sub '${AWS::StackName}-rest-api'
      Policy:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal: '*'
            Action: 'execute-api:Invoke'
            Resource: '*'
            Condition:
              IpAddress:
                aws:SourceIp:
                  - '1.2.3.4/32'  # Your IP
                  - '5.6.7.8/32'  # GroupMe IP (example)
```

**Note**: HTTP APIs don't support resource policies. You'd need to switch to REST API (more expensive).

---

### ✅ Option 5: Lambda Authorizer (Advanced)

**How it works**: Run custom authorization logic before Lambda execution.

**Pros**: Flexible, can implement any auth logic
**Cons**: More complex, adds latency

```python
# authorizer_lambda.py
def lambda_handler(event, context):
    token = event.get('headers', {}).get('Authorization')

    # Custom validation logic
    if token == os.environ.get('EXPECTED_TOKEN'):
        return {
            'principalId': 'user',
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [{
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Allow',
                    'Resource': event['methodArn']
                }]
            }
        }

    return {
        'principalId': 'user',
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': 'Deny',
                'Resource': event['methodArn']
            }]
        }
    }
```

**Problem**: GroupMe doesn't send custom headers, so this won't work for webhooks.

---

## Recommended Approach

### For Production:

**Use Option 1 (Secret URL) + Option 2 (Request Validation)**

1. **Secret URL**: Prevents random discovery
2. **Request Validation**: Catches malformed/suspicious requests
3. **Monitor CloudWatch**: Set up alarms for unusual activity

#### Implementation:

```bash
# 1. Generate secret
SECRET=$(openssl rand -hex 16)

# 2. Deploy with secret
sam deploy \
  --parameter-overrides \
    WebhookSecret=$SECRET \
    UseSecretsManager=true

# 3. Get webhook URL from output
aws cloudformation describe-stacks \
  --stack-name station95-chatbot-webhook \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
  --output text

# 4. Update GroupMe with secret URL
curl -X POST https://api.groupme.com/v3/bots/update \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\": \"$GROUPME_BOT_ID\", \"callback_url\": \"$WEBHOOK_URL\"}"

# 5. Never share the URL publicly!
```

---

## Manual Testing

For your own testing (separate from GroupMe), create a separate endpoint with API key:

Add to `template.yaml`:

```yaml
  TestEndpoint:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: 'POST /test'
      Target: !Sub 'integrations/${LambdaIntegration}'
      AuthorizationType: AWS_IAM  # Requires AWS credentials
```

Test with AWS credentials:
```bash
# Requires aws-cli and valid credentials
aws apigatewayv2 invoke \
  --api-id your-api-id \
  --stage $default \
  --path /test \
  --body '{"test": "data"}'
```

---

## Monitoring & Alerts

Set up CloudWatch alarms to detect suspicious activity:

```bash
# Alarm for too many requests
aws cloudwatch put-metric-alarm \
  --alarm-name webhook-too-many-requests \
  --alarm-description "Alert if webhook receives > 100 requests in 5 minutes" \
  --metric-name Count \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=station95-chatbot-webhook-webhook-handler

# Alarm for errors
aws cloudwatch put-metric-alarm \
  --alarm-name webhook-errors \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 60 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

---

## Cost Comparison

| Security Method | Monthly Cost | Effectiveness |
|----------------|--------------|---------------|
| Secret URL | $0 | ⭐⭐⭐⭐ |
| Request Validation | $0 | ⭐⭐⭐ |
| WAF | ~$5-10 | ⭐⭐⭐⭐⭐ |
| Resource Policy (REST API) | ~$3.50 extra | ⭐⭐⭐⭐ |
| Lambda Authorizer | ~$0.20 | N/A (doesn't work with GroupMe) |

**Recommendation**: Secret URL + Request Validation = **$0/month, ⭐⭐⭐⭐ effective**

---

## Security Checklist

- [x] Use secret URL path for webhook
- [x] Store secrets in AWS Secrets Manager
- [x] Validate webhook request structure
- [x] Check group_id matches expected group
- [x] Validate timestamp is recent
- [x] Monitor CloudWatch logs
- [x] Set up CloudWatch alarms
- [ ] Consider WAF for production (if budget allows)
- [x] Never commit secrets to git
- [x] Rotate webhook secret periodically (every 90 days)
- [x] Use HTTPS (API Gateway provides this)
- [x] Keep dependencies updated

---

## What GroupMe Doesn't Provide

❌ **No webhook signature**: GroupMe doesn't sign webhooks with HMAC like Slack/GitHub
❌ **No IP documentation**: GroupMe doesn't publish their IP ranges
❌ **No custom headers**: Can't add auth headers to webhooks

This is why **secret URL path** is the best option for GroupMe webhooks.
