# Azure resources

Subscription: Azure for Students
Resource group: `rg-lostfound`
Region: `centralindia` (eastus is blocked by a student-subscription region policy)

No secrets are stored in this file. The SQL admin password lives only in Key Vault.

| Resource | Name | Type / tier | URL / endpoint |
|---|---|---|---|
| Resource group | `rg-lostfound` | | https://portal.azure.com/#@/resource/subscriptions/6fd60ac2-02b8-4478-a250-10b7dc98b06c/resourceGroups/rg-lostfound |
| Key Vault | `kv-lostfound-abql7` | Standard | https://kv-lostfound-abql7.vault.azure.net/ |
| SQL server | `sql-lostfound-txjqe` | Azure SQL logical server, admin `lfadmin` | `sql-lostfound-txjqe.database.windows.net` |
| SQL database | `lostfound-db` | Free offer, GP_S_Gen5_2 serverless, auto-pause on free-limit exhaustion | on the server above |
| App Service plan | `plan-lostfound` | F1 (Free), Linux | |
| Web app | `app-lostfound-xlfzn` | Node 22 LTS | https://app-lostfound-xlfzn.azurewebsites.net |
| Computer Vision | `vision-lostfound-mdizs` | F0 (Free) | https://vision-lostfound-mdizs.cognitiveservices.azure.com/ |
| Virtual machine | not created | pending | see below |

## Secrets

- `sql-admin-password` in Key Vault `kv-lostfound-abql7` is the SQL admin password for `lfadmin`.

## Pending: virtual machine

`Standard_B1s` is capacity-restricted in centralindia for this subscription. All other B-series sizes are restricted too.
`Standard_F1als_v7` fails with quota 0, and `Standard_A1_v2` is capacity-restricted. No small size in centralindia is both available and within quota.
