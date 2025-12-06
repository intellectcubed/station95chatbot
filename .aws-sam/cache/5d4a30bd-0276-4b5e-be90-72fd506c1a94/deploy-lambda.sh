#!/bin/bash

# Deploy script for GroupMe Webhook Lambda
# This script packages the Lambda function and deploys it using CloudFormation

set -e

STACK_NAME="station95-chatbot-webhook"
REGION="us-east-1"  # Change to your preferred region
S3_BUCKET=""  # Will be created if not exists

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GroupMe Webhook Lambda Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if required environment variables are set
if [ -z "$GROUPME_BOT_ID" ] || [ -z "$GROUPME_API_TOKEN" ] || [ -z "$GROUPME_GROUP_ID" ]; then
    echo -e "${YELLOW}Warning: Required environment variables not set${NC}"
    echo "Please set the following environment variables:"
    echo "  - GROUPME_BOT_ID"
    echo "  - GROUPME_API_TOKEN"
    echo "  - GROUPME_GROUP_ID"
    echo "  - OPENAI_API_KEY (if using OpenAI)"
    echo "  - ANTHROPIC_API_KEY (if using Anthropic)"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}AWS Account ID: ${ACCOUNT_ID}${NC}"

# Set S3 bucket name based on account ID
S3_BUCKET="${STACK_NAME}-lambda-code-${ACCOUNT_ID}"

# Create S3 bucket if it doesn't exist
echo -e "${GREEN}Checking S3 bucket: ${S3_BUCKET}${NC}"
if ! aws s3 ls "s3://${S3_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Bucket exists"
else
    echo "Creating S3 bucket..."
    aws s3 mb "s3://${S3_BUCKET}" --region ${REGION}
fi

# Create deployment package
echo -e "${GREEN}Creating Lambda deployment package...${NC}"

# Create temporary directory for packaging
PACKAGE_DIR=$(mktemp -d)
echo "Using temporary directory: ${PACKAGE_DIR}"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -t "${PACKAGE_DIR}" --quiet

# Copy source code
echo "Copying source code..."
cp -r src/station95chatbot "${PACKAGE_DIR}/"
cp groupme_webhook_handler_lambda.py "${PACKAGE_DIR}/"

# Copy roster data (if exists)
if [ -d "data" ]; then
    echo "Copying data directory..."
    cp -r data "${PACKAGE_DIR}/"
fi

# Create zip file
echo "Creating ZIP file..."
cd "${PACKAGE_DIR}"
ZIP_FILE="${OLDPWD}/lambda-deployment-package.zip"
zip -r "${ZIP_FILE}" . -q
cd "${OLDPWD}"

# Clean up temp directory
rm -rf "${PACKAGE_DIR}"

echo -e "${GREEN}Package created: $(du -h ${ZIP_FILE} | cut -f1)${NC}"

# Upload to S3
echo -e "${GREEN}Uploading to S3...${NC}"
aws s3 cp "${ZIP_FILE}" "s3://${S3_BUCKET}/lambda-deployment-package.zip"

# Update CloudFormation template to use S3 location
echo -e "${GREEN}Preparing CloudFormation template...${NC}"
TEMPLATE_FILE="cloudformation-template.yaml"
UPDATED_TEMPLATE="cloudformation-template-updated.yaml"

# Replace the ZipFile with S3 bucket location
sed "s|ZipFile:.*|S3Bucket: ${S3_BUCKET}\n        S3Key: lambda-deployment-package.zip|" "${TEMPLATE_FILE}" > "${UPDATED_TEMPLATE}"

# Prepare CloudFormation parameters
echo -e "${GREEN}Preparing CloudFormation parameters...${NC}"

PARAMS=(
    "ParameterKey=GroupMeBotId,ParameterValue=${GROUPME_BOT_ID:-placeholder}"
    "ParameterKey=GroupMeApiToken,ParameterValue=${GROUPME_API_TOKEN:-placeholder}"
    "ParameterKey=GroupMeGroupId,ParameterValue=${GROUPME_GROUP_ID:-placeholder}"
    "ParameterKey=AIProvider,ParameterValue=${AI_PROVIDER:-openai}"
    "ParameterKey=OpenAIApiKey,ParameterValue=${OPENAI_API_KEY:-}"
    "ParameterKey=AnthropicApiKey,ParameterValue=${ANTHROPIC_API_KEY:-}"
    "ParameterKey=CalendarServiceUrl,ParameterValue=${CALENDAR_SERVICE_URL:-http://localhost:8000/commands}"
    "ParameterKey=ConfidenceThreshold,ParameterValue=${CONFIDENCE_THRESHOLD:-70}"
    "ParameterKey=LogLevel,ParameterValue=${LOG_LEVEL:-INFO}"
)

# Deploy CloudFormation stack
echo -e "${GREEN}Deploying CloudFormation stack: ${STACK_NAME}${NC}"

aws cloudformation deploy \
    --template-file "${UPDATED_TEMPLATE}" \
    --stack-name "${STACK_NAME}" \
    --parameter-overrides "${PARAMS[@]}" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "${REGION}"

# Get outputs
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo -e "${GREEN}Stack Outputs:${NC}"
aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

# Get webhook URL
WEBHOOK_URL=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
    --output text)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Next Steps:${NC}"
echo -e "${GREEN}========================================${NC}"
echo "1. Configure your GroupMe bot callback URL to:"
echo -e "   ${YELLOW}${WEBHOOK_URL}${NC}"
echo ""
echo "2. Test the webhook with:"
echo "   curl ${WEBHOOK_URL%/webhook}/health"
echo ""
echo "3. Monitor logs with:"
echo "   aws logs tail /aws/lambda/${STACK_NAME}-webhook-handler --follow"
echo ""

# Clean up
rm -f "${ZIP_FILE}" "${UPDATED_TEMPLATE}"

echo -e "${GREEN}Done!${NC}"
