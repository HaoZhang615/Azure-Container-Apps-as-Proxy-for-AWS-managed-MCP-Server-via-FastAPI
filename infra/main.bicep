targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@secure()
@description('AWS Client ID for authentication')
param awsClientId string

@secure()
@description('AWS Client Secret for authentication')
param awsClientSecret string

@description('AWS Auth URL for authentication')
param awsAuthUrl string

@description('AWS MCP URL for the service')
param awsMcpUrl string

@description('AWS Scope for authentication')
param awsScope string

// Tags that should be applied to all resources.
var tags = {
  'azd-env-name': environmentName
}

// Organize resources in a resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module resources 'resources.bicep' = {
  scope: rg
  name: 'resources'
  params: {
    location: location
    tags: tags
    awsClientId: awsClientId
    awsClientSecret: awsClientSecret
    awsAuthUrl: awsAuthUrl
    awsMcpUrl: awsMcpUrl
    awsScope: awsScope
  }
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.AZURE_CONTAINER_REGISTRY_ENDPOINT
output AZURE_CONTAINER_APP_URL string = resources.outputs.AZURE_CONTAINER_APP_URL
