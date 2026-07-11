// Datails pilot stamp — skeleton (Slice 0; deployed at Slice 3).
// One self-contained regional stamp (LD-23): region is a parameter so a later
// UAE North stamp is a redeployment of the same templates, not new templates.
// LD-29 resilience baked in from the first deployment: Postgres PITR
// (backup retention), Blob soft-delete + versioning, Application Insights,
// budget alert.

@description('Azure region for the whole stamp (LD-23, twice-amended 10 Jul 2026: westeurope and germanywestcentral both blocked Postgres for this subscription; founder ruled swedencentral — see DECISIONS.md).')
param location string = 'swedencentral'

@description('Deployment environment name (dev | prod).')
param environmentName string = 'dev'

@description('Monthly budget alert threshold in USD (LD-29).')
param monthlyBudgetUsd int = 500

@description('Email that receives budget alerts (Azure requires at least one contact).')
param budgetContactEmail string

@description('Deploy the container app + migrate job (false on the first run, before an image exists in ACR).')
param deployApps bool = false

@description('Backend image tag in ACR (set by the deploy workflow).')
param imageTag string = 'latest'

@description('Entra External ID tenant ID (LD-1).')
param entraTenantId string = '194ac953-cb8a-4e07-9890-65e73d2c024d'

@description('Entra audience = API app registration client ID (LD-1).')
param entraAudience string = '00d8c4ff-db9c-4533-b344-48e08cf3af73'

@description('PostgreSQL administrator login (password via Key Vault, never in code).')
param postgresAdminLogin string = 'datails_owner'

@secure()
@description('PostgreSQL administrator password (supplied at deploy time).')
param postgresAdminPassword string

var prefix = 'datails-${environmentName}'
var storagePrefix = replace(prefix, '-', '')

// --- Observability (LD-29) --------------------------------------------------

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-appinsights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// --- Secrets -----------------------------------------------------------------

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${prefix}-kv'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
  }
}

// --- Storage: raw payload snapshots (LD-4), soft-delete + versioning (LD-29) --

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${storagePrefix}snap'
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: { enabled: true, days: 30 }
    isVersioningEnabled: true
  }
}

// --- Database: PITR via backup retention (LD-29) ------------------------------

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: '${prefix}-pg'
  location: location
  sku: { name: 'Standard_B2s', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: 32 }
    backup: {
      backupRetentionDays: 14
      geoRedundantBackup: 'Disabled'
    }
  }
}

// --- Runtime: Azure Container Apps (LD-25) ------------------------------------

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-aca-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Postgres runs with public access; this built-in rule admits only
// Azure-internal traffic (the container apps). Founder/dev access is a
// separate explicit rule added via CLI when needed.
resource pgAllowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: postgres
  name: 'AllowAllAzureServicesAndResourcesWithinAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// --- Container registry -------------------------------------------------------

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: '${storagePrefix}acr'
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

// --- Backend container app + migration job (LD-25) ------------------------------

// User-assigned identity, created and role-granted BEFORE the apps: with a
// system-assigned identity the first revision pulls the image before its
// AcrPull/KV grants exist and provisioning expires.
resource appIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-app-identity'
  location: location
}

var backendImage = '${acr.properties.loginServer}/datails-backend:${imageTag}'
var entraAuthority = 'https://${entraTenantId}.ciamlogin.com/${entraTenantId}/v2.0'
var entraJwksUrl = 'https://datails.ciamlogin.com/${entraTenantId}/discovery/v2.0/keys'

var appSecrets = [
  {
    name: 'database-url'
    keyVaultUrl: '${keyVault.properties.vaultUri}secrets/database-url'
    identity: appIdentity.id
  }
  {
    name: 'database-migration-url'
    keyVaultUrl: '${keyVault.properties.vaultUri}secrets/database-migration-url'
    identity: appIdentity.id
  }
  {
    name: 'foundry-api-key'
    keyVaultUrl: '${keyVault.properties.vaultUri}secrets/foundry-api-key'
    identity: appIdentity.id
  }
]

var commonEnv = [
  { name: 'ENVIRONMENT', value: environmentName }
  { name: 'DATABASE_URL', secretRef: 'database-url' }
  { name: 'DATABASE_MIGRATION_URL', secretRef: 'database-migration-url' }
  { name: 'AI_BACKEND', value: 'azure_foundry' }
  { name: 'FOUNDRY_ENDPOINT', value: 'https://datails-dev-foundry.cognitiveservices.azure.com' }
  { name: 'FOUNDRY_API_KEY', secretRef: 'foundry-api-key' }
  { name: 'ENTRA_TENANT_ID', value: entraTenantId }
  { name: 'ENTRA_AUTHORITY', value: entraAuthority }
  { name: 'ENTRA_JWKS_URL', value: entraJwksUrl }
  { name: 'ENTRA_AUDIENCE', value: entraAudience }
  { name: 'BLOB_BACKEND', value: 'local' } // Azure Blob backend lands with the Slice 1 live acceptance
]

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = if (deployApps) {
  name: '${prefix}-api'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${appIdentity.id}': {} }
  }
  dependsOn: [identityAcrPull, identityKvRead]
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: appIdentity.id
        }
      ]
      secrets: appSecrets
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: commonEnv
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 2 }
    }
  }
}

resource migrateJob 'Microsoft.App/jobs@2024-03-01' = if (deployApps) {
  name: '${prefix}-migrate'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${appIdentity.id}': {} }
  }
  dependsOn: [identityAcrPull, identityKvRead]
  properties: {
    environmentId: containerAppsEnv.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 600
      replicaRetryLimit: 0
      manualTriggerConfig: { parallelism: 1, replicaCompletionCount: 1 }
      registries: [
        {
          server: acr.properties.loginServer
          identity: appIdentity.id
        }
      ]
      secrets: appSecrets
    }
    template: {
      containers: [
        {
          name: 'migrate'
          image: backendImage
          command: ['alembic', 'upgrade', 'head']
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: commonEnv
        }
      ]
    }
  }
}

// Managed-identity grants: image pull + Key Vault secret reads.
var acrPullRole = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d'
)
var kvSecretsUserRole = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6'
)

resource identityAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, 'acrpull', appIdentity.name)
  properties: {
    roleDefinitionId: acrPullRole
    principalId: appIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource identityKvRead 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  name: guid(keyVault.id, 'kvread', appIdentity.name)
  properties: {
    roleDefinitionId: kvSecretsUserRole
    principalId: appIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Budget alert (LD-29) ------------------------------------------------------

resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: '${prefix}-monthly-budget'
  properties: {
    category: 'Cost'
    amount: monthlyBudgetUsd
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: '2026-07-01'
      endDate: '2028-07-01'
    }
    notifications: {
      approaching: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        contactEmails: [budgetContactEmail]
      }
    }
  }
}

output keyVaultName string = keyVault.name
output storageAccountName string = storage.name
output postgresServerName string = postgres.name
output containerAppsEnvironmentId string = containerAppsEnv.id
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output acrLoginServer string = acr.properties.loginServer
output backendFqdn string = deployApps ? backendApp.properties.configuration.ingress.fqdn : ''
