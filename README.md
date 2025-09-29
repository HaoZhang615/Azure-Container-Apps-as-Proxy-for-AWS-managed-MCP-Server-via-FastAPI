# AWS MCP Server to Microsoft Copilot Studio Solution Accelerator

This solution provides a production-ready proxy that enables Microsoft Copilot Studio to communicate with AWS MCP (Model Context Protocol) servers through a FastAPI-based HTTP bridge.

## 🚀 Quick Start

### Prerequisites
- Azure subscription
- Azure Developer CLI (`azd`)
- AWS credentials with Bedrock access
- VS Code with Azure extensions

### 1. Set Up Environment Configuration

```bash
# Clone and navigate to the project
git clone https://github.com/HaoZhang615/Azure-Container-Apps-as-Proxy-for-AWS-managed-MCP-Server-via-FastAPI.git
cd Azure-Container-Apps-as-Proxy-for-AWS-managed-MCP-Server-via-FastAPI

# Copy the environment template
cp .env.template .env

# Edit .env file with your actual AWS credentials
AWS_CLIENT_ID=your_actual_client_id
AWS_CLIENT_SECRET=your_actual_client_secret
AWS_AUTH_URL=https://your-cognito-domain.auth.region.amazoncognito.com/oauth2/token
AWS_MCP_URL=https://bedrock-agentcore.region.amazonaws.com/runtimes/your-runtime-arn/invocations?qualifier=DEFAULT
AWS_SCOPE=your_actual_scope
```

### 2. Deploy to Azure

```bash
# Deploy infrastructure and application
# The .env values will be automatically loaded as environment variables
azd up
```

The deployment process will:
1. **Pre-deployment**: Automatically read your `.env` file and load all variables
2. **Validation**: Verify all required AWS credentials are set
3. **Infrastructure**: Deploy with Azure Key Vault for secure secret storage
4. **Application**: Build and deploy the container app with environment variables

**Note**: The azd hooks will automatically run regardless of which environment you're using, ensuring your `.env` file is always loaded before deployment.

### 3. Set Up Copilot Studio Custom Connector
1. In Copilot Studio, create a new Custom Connector ([learn more from full tutorial](https://github.com/microsoft/mcsmcp?tab=readme-ov-file) )
2. Use your deployed Azure Container App URL as the base URL
3. Configure POST requests to `/mcp` endpoint
4. Set authentication to "No Authentication" (handled internally)

## ⚙️ Configuration

### Environment Setup

The project uses a `.env` file for configuration. Copy `.env.template` to `.env` and fill in your values:

```bash
cp .env.template .env
```

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_CLIENT_ID` | AWS Cognito Client ID | `2p3li5ek3...` |
| `AWS_CLIENT_SECRET` | AWS Cognito Client Secret | `1ok90cr91cmjlj...` |
| `AWS_AUTH_URL` | Cognito OAuth2 token endpoint | `https://<your-cognito-domain>.amazoncognito.com/oauth2/token` |
| `AWS_MCP_URL` | AWS MCP server endpoint | `https://<your-bedrock-region>.amazonaws.com/runtimes/arn...` |
| `AWS_SCOPE` | OAuth2 scope for AWS access | `<your-scope>/read` |

### Security Notes

- The `.env` file is automatically ignored by git (in `.gitignore`)
- Values are securely stored in Azure Key Vault during deployment
- AWS_CLIENT_SECRET is stored as a Key Vault secret, not plain text
- Environment variables are automatically loaded by azd hooks

## 📁 Project Structure

```
├── main.py                 # FastAPI proxy server
├── pyproject.toml         # Python dependencies
├── Dockerfile             # Production container config
├── azure.yaml             # Azure Developer CLI config with hooks
├── .env.template          # Environment template (copy to .env)
├── .env                   # Your environment variables (gitignored)
└── infra/                 # Azure infrastructure (Bicep)
    ├── main.bicep         # Main infrastructure template  
    ├── main.parameters.json # Infrastructure parameters
    └── resources.bicep    # Resource definitions with Key Vault
```

## 🏗️ Architecture

```
Copilot Studio → Custom Connector → Azure Container App → AWS MCP Server
                                   (This Solution)
```

The proxy handles:
- AWS Cognito OAuth2 authentication
- MCP protocol translation
- HTTP status code normalization
- Error handling and logging
- Secure credential management via Azure Key Vault

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3000` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level |

## 🔧 Customization

### Modify AWS Authentication
Edit the `get_aws_token()` function in `main.py`:

```python
async def get_aws_token():
    # Your custom AWS authentication logic
    pass
```

### Add Request Validation
Extend the `validate_mcp_request()` function:

```python
def validate_mcp_request(request_data):
    # Your custom validation logic
    pass
```

### Change Response Processing
Modify the `process_aws_response()` function:

```python
def process_aws_response(aws_response):
    # Your custom response processing
    pass
```

## 🐛 Troubleshooting

### Common Issues

1. **Empty responses from AWS**
   - Check AWS credentials configuration
   - Verify MCP server endpoint URL
   - Review Azure Container App logs

2. **Authentication failures**
   - Validate AWS_CLIENT_ID and AWS_CLIENT_SECRET
   - Check Cognito domain in AWS_AUTH_URL
   - Ensure proper OAuth2 scopes

3. **Copilot Studio connection errors**
   - Verify Custom Connector configuration
   - Check Azure Container App is running
   - Review network connectivity

### Debugging

Enable detailed logging by setting environment variable:
```bash
LOG_LEVEL=DEBUG
```

View Azure Container App logs:
```bash
azd logs
```

## 📊 Monitoring

The solution includes:
- Health check endpoint at `/health`
- Structured logging with correlation IDs
- Azure Application Insights integration (via Container App)

## 🔒 Security

- AWS credentials stored as Azure Container App environment variables
- No sensitive data in source code
- HTTPS enforced through Azure Container App
- CORS configured for security

## 🚀 Production Deployment

The solution is production-ready with:
- Multi-stage Docker build for optimization
- Health checks for reliability
- Minimal dependencies for security
- Azure Container Apps for scalability
- Infrastructure as Code with Bicep

## 📚 Additional Resources

- [Azure Container Apps Documentation](https://docs.microsoft.com/azure/container-apps/)
- [Microsoft Copilot Studio Custom Connectors](https://docs.microsoft.com/power-platform/copilot-studio/)
- [AWS MCP Protocol](https://aws.amazon.com/bedrock/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
