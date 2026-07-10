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

// Backend container app: image + env wiring completed at Slice 3 deploy.
// Kept as skeleton so the stamp shape is reviewable now.

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
