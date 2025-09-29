@description('The location used for all deployed resources')
param location string = resourceGroup().location

@description('Tags that will be applied to all resources')
param tags object = {}

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

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = uniqueString(subscription().id, resourceGroup().id, location)

// Monitor application with Azure Monitor
module monitoring 'br/public:avm/ptn/azd/monitoring:0.1.0' = {
  name: 'monitoring'
  params: {
    logAnalyticsName: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: '${abbrs.insightsComponents}${resourceToken}'
    applicationInsightsDashboardName: '${abbrs.portalDashboards}${resourceToken}'
    location: location
    tags: tags
  }
}

// Container registry
module containerRegistry 'br/public:avm/res/container-registry/registry:0.1.1' = {
  name: 'registry'
  params: {
    name: '${abbrs.containerRegistryRegistries}${resourceToken}'
    location: location
    tags: tags
    publicNetworkAccess: 'Enabled'
    roleAssignments: [
      {
        principalId: proxyIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
      }
    ]
  }
}

// Key Vault for storing secrets
module keyVault 'br/public:avm/res/key-vault/vault:0.6.2' = {
  name: 'keyvault'
  params: {
    name: '${abbrs.keyVaultVaults}${resourceToken}'
    location: location
    tags: tags
    enableVaultForTemplateDeployment: true
    roleAssignments: [
      {
        principalId: proxyIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
      }
    ]
    secrets: [
      {
        name: 'aws-client-secret'
        value: awsClientSecret
      }
    ]
  }
}

// Container apps environment
module containerAppsEnvironment 'br/public:avm/res/app/managed-environment:0.4.5' = {
  name: 'container-apps-environment'
  params: {
    logAnalyticsWorkspaceResourceId: monitoring.outputs.logAnalyticsWorkspaceResourceId
    name: '${abbrs.appManagedEnvironments}${resourceToken}'
    location: location
    zoneRedundant: false
  }
}

// User-assigned managed identity for the container app
module proxyIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.2.1' = {
  name: 'proxyidentity'
  params: {
    name: '${abbrs.managedIdentityUserAssignedIdentities}proxy-${resourceToken}'
    location: location
  }
}

// Container app for the MCP proxy
module proxyContainerApp 'br/public:avm/res/app/container-app:0.8.0' = {
  name: 'proxy-container-app'
  params: {
    name: 'dsm-aws-mcp-proxy'
    ingressTargetPort: 3000
    scaleMinReplicas: 1
    scaleMaxReplicas: 3
    secrets: {
      secureList: [
        {
          name: 'aws-client-secret'
          keyVaultUrl: '${keyVault.outputs.uri}secrets/aws-client-secret'
          identity: proxyIdentity.outputs.resourceId
        }
      ]
    }
    containers: [
      {
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        name: 'proxy'
        resources: {
          cpu: json('0.5')
          memory: '1.0Gi'
        }
        env: [
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: monitoring.outputs.applicationInsightsConnectionString
          }
          {
            name: 'AZURE_CLIENT_ID'
            value: proxyIdentity.outputs.clientId
          }
          {
            name: 'PORT'
            value: '3000'
          }
          {
            name: 'AWS_AUTH_URL'
            value: awsAuthUrl
          }
          {
            name: 'AWS_MCP_URL'
            value: awsMcpUrl
          }
          {
            name: 'AWS_CLIENT_ID'
            value: awsClientId
          }
          {
            name: 'AWS_CLIENT_SECRET'
            secretRef: 'aws-client-secret'
          }
          {
            name: 'AWS_SCOPE'
            value: awsScope
          }
          {
            name: 'LOG_LEVEL'
            value: 'INFO'
          }
        ]
      }
    ]
    managedIdentities: {
      systemAssigned: false
      userAssignedResourceIds: [proxyIdentity.outputs.resourceId]
    }
    registries: [
      {
        server: containerRegistry.outputs.loginServer
        identity: proxyIdentity.outputs.resourceId
      }
    ]
    ingressExternal: true
    environmentResourceId: containerAppsEnvironment.outputs.resourceId
    location: location
    tags: union(tags, { 'azd-service-name': 'proxy' })
  }
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer
output AZURE_CONTAINER_APP_URL string = 'https://${proxyContainerApp.outputs.fqdn}'
