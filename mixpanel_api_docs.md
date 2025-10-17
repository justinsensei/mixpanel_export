# Mixpanel API Documentation

## Table of Contents
- [Overview](#overview)
- [Service Accounts Authentication](#service-accounts-authentication)
- [Raw Data Export API](#raw-data-export-api)

---

## Overview

The Mixpanel Export Data APIs allow you to export your raw data either manually or through a pipeline.

### Key Use Cases

1. **Analyzing Data Spikes** - Compare event sources to understand anomalies
2. **Migrating Events** - Transfer events between Mixpanel projects
3. **Custom Analysis** - Perform specialized analysis beyond standard Mixpanel capabilities

### API Categories

Mixpanel provides multiple API categories for different purposes:

- **Ingestion API** - Event tracking, user/group profiles, lookup tables
- **Query API** - Cohorts, funnels, retention, segmentation reports
- **Event Export API** - Raw data downloads
- **Identity API** - Profile management and merging
- **Lexicon Schemas API** - Schema creation and management
- **Data Pipelines API** - Pipeline creation and management
- **Service Accounts API** - Account administration
- **Annotations API** - Metadata management
- **GDPR API** - Data retrieval and deletion
- **Warehouse Connectors API** - Import operations

### Authentication Methods

Mixpanel supports multiple authentication approaches:
- **Service Accounts** (recommended)
- **Project Tokens**
- **Project Secret** (deprecated)
- **Request Signature** (deprecated)

See [Service Accounts Authentication](#service-accounts-authentication) for detailed implementation guide.

### Rate Limits

Rate limits apply to API requests. Specific thresholds vary by endpoint and account type.

---

## Service Accounts Authentication

Service accounts represent non-human entities like scripts or backend services. They are the **recommended authentication method** for programmatic API access.

### Overview

Service accounts function like regular Mixpanel users but are designed for automated access. They can be granted permissions across multiple projects and workspaces within an organization.

### Authentication Method

Service accounts use **HTTP Basic Authentication** with either base64-encoded or plain-text credentials.

#### Required Credentials

- **Username**: The service account username
- **Secret**: The service account secret key

### Implementation Examples

#### cURL with --user flag
```bash
curl https://mixpanel.com/api/app/me \
  --user "<serviceaccount_username>:<serviceaccount_secret>"
```

#### cURL with Authorization header
```bash
curl https://mixpanel.com/api/app/me \
  --header 'authorization: Basic <serviceaccount_username>:<serviceaccount_secret>'
```

#### Python Requests
```python
import requests
requests.get(
  'https://mixpanel.com/api/app/me',
  auth=('<serviceaccount_username>', '<serviceaccount_secret>')
)
```

### Creating Service Accounts

**Permission Requirements:** Owner or Admin role required

Service accounts can be created through:

1. **Organization Settings** - Manage organization-wide service accounts
2. **Project Settings** - Create project-specific accounts (automatically assigned admin role)

### Security Best Practices

⚠️ **CRITICAL**: Save your service account secret immediately after creation. You won't be able to access it again.

- Store credentials in secure vaults or environment variables
- Never commit secrets to version control
- Rotate credentials regularly using expiration settings

### Credential Expiration

- Service accounts default to **no expiration**
- Optional time-limited credentials can be configured
- Expired credentials will be rejected by the API
- Supports credential rotation policies

### Permissions & Scope

Service accounts inherit permissions based on assigned roles within each project or workspace, enabling granular access control across your organization.

---

## Raw Data Export API

### Authentication

The Raw Data Export API supports two authentication methods:

#### 1. Service Account Authentication (Recommended)

When using service accounts with the Raw Data Export API:

**Required Query Parameter:**
- `project_id` must be included in all requests

**Example:**
```
https://data.mixpanel.com/api/2.0/export?project_id=12345
```

**Classified Data Access:**
- For projects with classified data, the service account must have explicit permission to access that classified information

#### 2. Project Secret Authentication

The API also supports project secret-based authentication (see Project Secret documentation for details).

### Raw Event Export Endpoint

Export raw event data from Mixpanel with all event properties, including distinct_id and exact timestamps.

#### Endpoint

```
GET https://data.mixpanel.com/api/2.0/export
```

#### Overview

The Raw Event Export API allows you to download your event data as JSON as it is received and stored within Mixpanel, complete with:
- All event properties
- distinct_id
- Exact timestamp when the event was fired

#### Query Parameters

**Required:**
- `project_id` (integer) - Your Mixpanel project ID (required when using Service Account authentication)
- `from_date` (string) - The date in yyyy-mm-dd format to begin querying from. This date is inclusive and interpreted as UTC timezone for projects created after 1 January 2023 and current project timezone for projects created before 11 January 2023.
- `to_date` (string) - The date in yyyy-mm-dd format to query to. This date is inclusive and interpreted as UTC timezone for projects created after 1 January 2023 and current project timezone for projects created before 11 January 2023.

**Optional:**
- `limit` (integer) - Limit the max number of events to be returned. Value cannot be over 100000.
- `event` (string) - The event or events that you wish to get data for, encoded as a JSON array.
- `where` (string) - An expression to filter events by. [More info on expression sequence structure](https://developer.mixpanel.com/reference/segmentation-expressions)
- `time_in_ms` (boolean) - Defaults to `false` which exports event timestamps with second-precision. Set to `true` to export event timestamps with millisecond-precision.

#### Request Headers

- **Authorization**: Basic authentication with base64 encoded credentials
  - Format: `Basic <serviceaccount_username>:<serviceaccount_secret>`
- **Accept-Encoding** (optional): String enum
  - If set to `gzip` and the response body is > 1400 bytes, the response will be compressed with gzip, and `Content-Encoding` will be set to `gzip`
  - Allowed values: `gzip`

#### Response Format

**200 Success**

The returned format is **JSONL** (JSON Lines) - one event per line where each line is a valid JSON object, but the full return itself is JSONL.

Example response structure:
- Each line contains a complete event object
- Events include all properties, distinct_id, and timestamps
- Response may be gzip compressed if `Accept-Encoding: gzip` header is used and response > 1400 bytes

#### Rate Limits

- **60 queries per hour**
- **3 queries per second**
- **Maximum 100 concurrent queries**
- Returns `429` error if rate limit is exceeded

#### Code Examples

##### cURL

```bash
curl --request GET \
     --url 'https://data.mixpanel.com/api/2.0/export?project_id=YOUR_PROJECT_ID&from_date=2024-01-01&to_date=2024-01-31' \
     --user 'SERVICE_ACCOUNT_USERNAME:SERVICE_ACCOUNT_SECRET' \
     --header 'accept: text/plain'
```

**Note:** Replace `YOUR_PROJECT_ID`, `SERVICE_ACCOUNT_USERNAME`, and `SERVICE_ACCOUNT_SECRET` with your actual credentials.

##### Python

```python
import requests

url = "https://data.mixpanel.com/api/2.0/export"

headers = {"accept": "text/plain"}

params = {
    "project_id": "YOUR_PROJECT_ID",
    "from_date": "2024-01-01",
    "to_date": "2024-01-31"
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    auth=("SERVICE_ACCOUNT_USERNAME", "SERVICE_ACCOUNT_SECRET")
)

print(response.text)
```

**Note:** Replace `YOUR_PROJECT_ID`, `SERVICE_ACCOUNT_USERNAME`, and `SERVICE_ACCOUNT_SECRET` with your actual credentials.

---

*Last updated: 2025-10-17*
