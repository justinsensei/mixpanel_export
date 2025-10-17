# Mixpanel Export Script - Technical Specification

## Document Information

**Version:** 1.0
**Last Updated:** 2025-10-17
**Status:** Draft

---

## 1. Overview

### 1.1 Purpose

Build a Python script that exports historical event data from Mixpanel and saves it locally as uncompressed JSONL files. These files will be compatible with PostHog's S3 import feature (Mixpanel content type) for manual upload.

### 1.2 Scope

**In Scope:**
- Interactive date range selection
- Mixpanel Raw Data Export API integration
- Service Account authentication
- Local JSONL file creation (uncompressed)
- Descriptive filename generation
- Basic error handling and user feedback

**Out of Scope:**
- Automatic S3 upload (manual upload via AWS CLI/console)
- Automatic date range batching/splitting
- Advanced data validation and quality checks
- Retry logic and rate limit handling
- Data transformation (PostHog handles this)

### 1.3 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Output Format** | Uncompressed JSONL | PostHog requirement for S3 imports |
| **API Response** | No gzip encoding | Simpler implementation, easier debugging |
| **File Storage** | Local filesystem only | Simplifies script, manual S3 upload gives user control |
| **Date Input** | Runtime prompts | Flexibility for different export ranges |
| **Timestamp Precision** | Milliseconds (`time_in_ms=true`) | Best practice for accurate event ordering |

---

## 2. System Architecture

### 2.1 High-Level Flow

```
┌─────────────┐
│    User     │
│  (Console)  │
└──────┬──────┘
       │ 1. Enters date range
       ↓
┌─────────────────────┐
│   Python Script     │
│                     │
│ 2. Load .env        │
│ 3. Validate inputs  │
│ 4. Build API request│
└──────┬──────────────┘
       │ 5. HTTP GET with Basic Auth
       ↓
┌─────────────────────┐
│  Mixpanel API       │
│  (Raw Export)       │
└──────┬──────────────┘
       │ 6. JSONL response
       ↓
┌─────────────────────┐
│   Python Script     │
│                     │
│ 7. Write to file    │
│ 8. Confirm success  │
└──────┬──────────────┘
       │ 9. JSONL file created
       ↓
┌─────────────────────┐
│  Local Filesystem   │
│                     │
│  mixpanel_export_   │
│  YYYY-MM-DD_to_     │
│  YYYY-MM-DD.jsonl   │
└─────────────────────┘
```

### 2.2 Components

**2.2.1 Main Script (`export_mixpanel.py`)**
- Entry point
- User interaction (date range prompts)
- Orchestrates export process

**2.2.2 Configuration Module**
- Loads environment variables from `.env`
- Validates required credentials exist
- Provides configuration to other modules

**2.2.3 API Client Module**
- Constructs Mixpanel API requests
- Handles authentication
- Executes HTTP requests
- Returns response data

**2.2.4 File Writer Module**
- Generates filename from date range
- Writes JSONL data to disk
- Handles file I/O errors

---

## 3. Technical Requirements

### 3.1 Environment Configuration

**Required Environment Variables** (from `.env` file):

| Variable | Type | Example | Description |
|----------|------|---------|-------------|
| `MIXPANEL_SERVICE_ACCOUNT_USERNAME` | string | `user.abc123.mp-service-account` | Service account username |
| `MIXPANEL_SERVICE_ACCOUNT_SECRET` | string | `QGsjHDzs8h...` | Service account secret |
| `MIXPANEL_PROJECT_ID` | integer | `1953473` | Mixpanel project ID |

**Optional Environment Variables:**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MIXPANEL_API_BASE_URL` | string | `https://data.mixpanel.com/api/2.0` | API base URL |
| `EXPORT_OUTPUT_DIR` | string | `./exports` | Directory for export files |

### 3.2 API Integration

**Endpoint:**
```
GET https://data.mixpanel.com/api/2.0/export
```

**Authentication:**
- Method: HTTP Basic Auth
- Format: `username:secret` (Service Account credentials)

**Required Query Parameters:**

| Parameter | Type | Source | Example |
|-----------|------|--------|---------|
| `project_id` | integer | Environment variable | `1953473` |
| `from_date` | string (YYYY-MM-DD) | User input | `2024-01-01` |
| `to_date` | string (YYYY-MM-DD) | User input | `2024-01-31` |
| `time_in_ms` | boolean | Hard-coded `true` | `true` |

**Request Headers:**

| Header | Value | Purpose |
|--------|-------|---------|
| `Accept` | `text/plain` | Indicate JSONL response expected |

**Response Format:**
- Content-Type: `text/plain` (JSONL)
- Body: Newline-delimited JSON objects
- One event per line
- No compression

**Example Response:**
```jsonl
{"event":"PageView","properties":{"distinct_id":"user123","time":1704067200000,"$browser":"Chrome"}}
{"event":"ButtonClick","properties":{"distinct_id":"user456","time":1704067260000,"button":"signup"}}
```

### 3.3 Rate Limits (Awareness)

**Mixpanel API Limits:**
- 60 queries per hour
- 3 queries per second
- Max 100 concurrent queries

**Handling Strategy (v1):**
- No automatic retry logic
- Display error message if 429 (rate limit) returned
- User manually waits and re-runs script

### 3.4 File Output Specification

**File Format:**
- Extension: `.jsonl`
- Content: Uncompressed JSON Lines
- Encoding: UTF-8
- Each line: Valid JSON object (one event)

**Filename Convention:**
```
mixpanel_export_{from_date}_to_{to_date}.jsonl
```

**Examples:**
- `mixpanel_export_2024-01-01_to_2024-01-31.jsonl`
- `mixpanel_export_2023-06-15_to_2024-06-14.jsonl`

**Output Directory:**
- Default: `./exports/` (created if doesn't exist)
- Configurable via `EXPORT_OUTPUT_DIR` environment variable

### 3.5 Date Range Validation

**Input Format:**
- Format: `YYYY-MM-DD`
- Example: `2024-01-01`

**Validation Rules:**

| Rule | Validation | Action on Failure |
|------|------------|-------------------|
| Valid date format | Must match `YYYY-MM-DD` | Display error, re-prompt |
| Date exists | Must be valid calendar date | Display error, re-prompt |
| End after start | `to_date >= from_date` | Display error, re-prompt |
| PostHog compatibility | Warn if range > 365 days | Display warning, allow continue |
| Not future dates | Dates must be <= today | Display error, re-prompt |

**PostHog 1-Year Limit Warning:**
```
⚠️  Warning: Date range exceeds 365 days.
PostHog imports support maximum 1-year ranges.
You may need to split this export before importing.

Continue anyway? (y/n):
```

---

## 4. Data Flow

### 4.1 Export Process Flow

```
START
  ↓
1. Load environment variables
  ↓
2. Validate required credentials exist
  ↓
3. Display welcome message
  ↓
4. Prompt user for from_date
  ↓
5. Validate from_date format
  ↓
6. Prompt user for to_date
  ↓
7. Validate to_date format and range
  ↓
8. Check if range > 365 days → [Show warning, confirm continue]
  ↓
9. Display export summary (dates, project, filename)
  ↓
10. Confirm export → [y/n]
  ↓
11. Make API request with Basic Auth
  ↓
12. Check response status
    ├─ 200 OK → Continue
    ├─ 401 → Display auth error, EXIT
    ├─ 429 → Display rate limit error, EXIT
    └─ Other → Display error, EXIT
  ↓
13. Create output directory if needed
  ↓
14. Write response body to JSONL file
  ↓
15. Display success message with:
    - File path
    - File size
    - Event count (lines in file)
    - Next steps (manual S3 upload)
  ↓
END
```

### 4.2 Error Handling

**Error Categories:**

| Category | Examples | Handling Strategy |
|----------|----------|-------------------|
| **Configuration Errors** | Missing .env, missing credentials | Display helpful error message, exit gracefully |
| **Input Validation Errors** | Invalid date format, invalid range | Display error, re-prompt user |
| **API Errors** | 401 Unauthorized, 429 Rate Limit, 500 Server Error | Display error with status code, suggest action, exit |
| **File I/O Errors** | Disk full, permission denied | Display error, check disk space, exit |
| **Network Errors** | Connection timeout, DNS failure | Display error with details, suggest retry, exit |

**Error Message Format:**
```
❌ Error: [Category]
   Details: [Specific error message]
   Action: [What user should do next]
```

**Example Error Messages:**

```
❌ Error: Missing Configuration
   Details: MIXPANEL_SERVICE_ACCOUNT_USERNAME not found in .env
   Action: Check your .env file and ensure all required variables are set

❌ Error: API Authentication Failed (401)
   Details: Invalid service account credentials
   Action: Verify credentials in .env are correct and not expired

❌ Error: Rate Limit Exceeded (429)
   Details: Mixpanel API rate limit reached (60 requests/hour)
   Action: Wait before retrying (limits reset hourly)
```

---

## 5. Implementation Details

### 5.1 Technology Stack

**Language:** Python 3.8+

**Required Dependencies:**
```
requests==2.31.0       # HTTP client
python-dotenv==1.0.0   # Environment variable loading
```

**Standard Library Modules:**
- `os` - File path operations
- `sys` - Exit handling
- `datetime` - Date validation
- `json` - Response validation (optional)
- `pathlib` - Path handling

### 5.2 Project Structure

```
mixpanel_export/
├── .env                          # Environment configuration (gitignored)
├── .env.example                  # Template for .env
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── README.md                     # Usage instructions
├── REQUIREMENTS.md               # Business requirements
├── SPEC.md                       # This technical specification
├── mixpanel_api_docs.md         # API reference documentation
├── posthog_import_docs.md       # PostHog import documentation
├── export_mixpanel.py           # Main script entry point
└── exports/                      # Output directory (gitignored)
    └── mixpanel_export_*.jsonl  # Generated export files
```

### 5.3 Code Organization

**Suggested Module Structure:**

```python
# export_mixpanel.py (main entry point)
def main():
    config = load_config()
    from_date, to_date = get_date_range_from_user()
    validate_date_range(from_date, to_date)
    confirm_export(from_date, to_date, config)
    data = export_from_mixpanel(config, from_date, to_date)
    filepath = save_to_file(data, from_date, to_date)
    display_success(filepath)

# config.py (configuration management)
def load_config():
    # Load and validate environment variables
    pass

# api_client.py (Mixpanel API interaction)
def export_from_mixpanel(config, from_date, to_date):
    # Build request, authenticate, fetch data
    pass

# file_writer.py (file operations)
def save_to_file(data, from_date, to_date):
    # Generate filename, write JSONL
    pass

# validators.py (input validation)
def validate_date_format(date_string):
    pass

def validate_date_range(from_date, to_date):
    pass
```

### 5.4 Key Functions Specification

**Function: `load_config()`**
- **Purpose:** Load and validate environment variables
- **Returns:** Dictionary with credentials and config
- **Raises:** `ConfigurationError` if required variables missing

**Function: `get_date_range_from_user()`**
- **Purpose:** Interactive prompts for date range
- **Returns:** Tuple of (from_date, to_date) as strings
- **Validation:** Date format, valid dates, logical range

**Function: `export_from_mixpanel(config, from_date, to_date)`**
- **Purpose:** Call Mixpanel API and retrieve data
- **Parameters:**
  - `config`: Dict with credentials and project_id
  - `from_date`: String (YYYY-MM-DD)
  - `to_date`: String (YYYY-MM-DD)
- **Returns:** String (JSONL response body)
- **Raises:** `APIError` for HTTP errors

**Function: `save_to_file(data, from_date, to_date)`**
- **Purpose:** Write JSONL data to local file
- **Parameters:**
  - `data`: String (JSONL content)
  - `from_date`: String (YYYY-MM-DD)
  - `to_date`: String (YYYY-MM-DD)
- **Returns:** String (full file path)
- **Raises:** `FileWriteError` for I/O errors

---

## 6. User Interface

### 6.1 Console Interaction

**Welcome Screen:**
```
╔════════════════════════════════════════════════╗
║   Mixpanel to PostHog Export Tool             ║
║   Export raw event data for S3 import         ║
╚════════════════════════════════════════════════╝

Loaded configuration:
  Project ID: 1953473
  Service Account: jdg_api_service.b3c8eb
  Output Directory: ./exports/
```

**Date Range Input:**
```
Enter export date range:

From date (YYYY-MM-DD): 2024-01-01
To date (YYYY-MM-DD): 2024-01-31

✓ Date range validated: 31 days
```

**Export Confirmation:**
```
Export Summary:
  Date Range: 2024-01-01 to 2024-01-31 (31 days)
  Project ID: 1953473
  Output File: mixpanel_export_2024-01-01_to_2024-01-31.jsonl

Proceed with export? (y/n): y
```

**Progress Indication:**
```
Exporting data from Mixpanel...
✓ API request successful
✓ Writing to file: exports/mixpanel_export_2024-01-01_to_2024-01-31.jsonl
```

**Success Message:**
```
✅ Export completed successfully!

File Details:
  Path: /Users/justingoff/Documents/mixpanel_export/exports/mixpanel_export_2024-01-01_to_2024-01-31.jsonl
  Size: 45.3 MB
  Events: 123,456 events

Next Steps:
  1. Verify the export file (check first/last lines)
  2. Upload to S3 bucket for PostHog import
  3. In PostHog import settings, set content type to "mixpanel"

Upload command (example):
  aws s3 cp exports/mixpanel_export_2024-01-01_to_2024-01-31.jsonl \
    s3://your-bucket-name/ \
    --metadata content-type=mixpanel
```

### 6.2 User Input Validation Feedback

**Invalid Date Format:**
```
Enter from date (YYYY-MM-DD): 01/01/2024
❌ Invalid format. Please use YYYY-MM-DD (e.g., 2024-01-01)
From date (YYYY-MM-DD):
```

**Invalid Date Range:**
```
From date (YYYY-MM-DD): 2024-06-01
To date (YYYY-MM-DD): 2024-01-01
❌ End date must be on or after start date
To date (YYYY-MM-DD):
```

**Future Date Warning:**
```
From date (YYYY-MM-DD): 2025-12-01
❌ Date cannot be in the future (today is 2025-10-17)
From date (YYYY-MM-DD):
```

**PostHog 1-Year Warning:**
```
From date (YYYY-MM-DD): 2023-01-01
To date (YYYY-MM-DD): 2024-12-31

⚠️  Warning: Date range is 730 days (2 years)
    PostHog S3 imports support maximum 1-year ranges.
    You will need to split this file before importing to PostHog.

Continue with export? (y/n):
```

---

## 7. Testing Strategy

### 7.1 Test Scenarios

**Configuration Tests:**
- ✓ Script loads .env successfully
- ✓ Script detects missing required environment variables
- ✓ Script validates service account credentials format

**Input Validation Tests:**
- ✓ Accepts valid date in YYYY-MM-DD format
- ✓ Rejects invalid date formats
- ✓ Rejects invalid calendar dates (e.g., 2024-02-30)
- ✓ Rejects end_date before start_date
- ✓ Rejects future dates
- ✓ Warns for date ranges > 365 days

**API Integration Tests:**
- ✓ Successfully authenticates with valid credentials
- ✓ Handles 401 authentication errors gracefully
- ✓ Handles 429 rate limit errors with helpful message
- ✓ Retrieves JSONL data for valid date range

**File Output Tests:**
- ✓ Creates exports directory if it doesn't exist
- ✓ Generates correctly formatted filename
- ✓ Writes valid JSONL content (one JSON object per line)
- ✓ File is uncompressed
- ✓ Handles disk space errors gracefully

**End-to-End Tests:**
- ✓ Complete export flow with 1-day range
- ✓ Complete export flow with 30-day range
- ✓ Verify output file is compatible with PostHog S3 import

### 7.2 Manual Testing Checklist

**Pre-Deployment:**
- [ ] Run export for 1-day range
- [ ] Run export for 30-day range
- [ ] Run export for 365-day range (with warning)
- [ ] Verify JSONL format validity (sample check)
- [ ] Test with invalid credentials
- [ ] Test with missing .env file
- [ ] Test all date validation scenarios
- [ ] Verify file sizes match expectations
- [ ] Check exports directory creation
- [ ] Verify filename generation

**PostHog Compatibility:**
- [ ] Upload test file to S3
- [ ] Import to PostHog with content_type="mixpanel"
- [ ] Verify events appear in PostHog
- [ ] Verify event transformations applied correctly

---

## 8. Deployment & Usage

### 8.1 Installation

**Prerequisites:**
- Python 3.8 or higher
- pip package manager
- Mixpanel Service Account credentials
- Git (for cloning repository)

**Setup Steps:**
```bash
# 1. Clone or navigate to repository
cd /Users/justingoff/Documents/mixpanel_export

# 2. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your Mixpanel credentials

# 5. Verify configuration
python export_mixpanel.py --check-config  # (if implemented)
```

### 8.2 Usage

**Basic Export:**
```bash
python export_mixpanel.py
```
*Follow interactive prompts for date range*

**Example Session:**
```bash
$ python export_mixpanel.py

Mixpanel to PostHog Export Tool
================================

From date (YYYY-MM-DD): 2024-01-01
To date (YYYY-MM-DD): 2024-01-31

Export Summary:
  Date Range: 2024-01-01 to 2024-01-31 (31 days)
  Output: mixpanel_export_2024-01-01_to_2024-01-31.jsonl

Proceed? (y/n): y

Exporting... ✓
File saved: exports/mixpanel_export_2024-01-01_to_2024-01-31.jsonl
Size: 45.3 MB | Events: 123,456
```

### 8.3 PostHog Import Workflow

**Step 1: Export from Mixpanel**
```bash
python export_mixpanel.py
# Enter date range when prompted
# Wait for export to complete
```

**Step 2: Upload to S3**
```bash
# Using AWS CLI
aws s3 cp exports/mixpanel_export_2024-01-01_to_2024-01-31.jsonl \
  s3://your-posthog-import-bucket/ \
  --metadata content-type=mixpanel
```

**Step 3: Configure PostHog Import**
1. Go to PostHog [Managed Migrations](https://app.posthog.com/managed_migrations)
2. Select "S3 Import"
3. Provide:
   - S3 Region: `us-east-1` (or your region)
   - S3 Bucket: `your-posthog-import-bucket`
   - AWS Access Key ID: `[your-key]`
   - AWS Secret Access Key: `[your-secret]`
   - **Content Type: `mixpanel`** ⚠️ Critical setting
4. Start import

**Step 4: Monitor Import**
- Watch migration dashboard for progress
- Verify events appear in PostHog
- Check event transformations are correct

---

## 9. Limitations & Future Enhancements

### 9.1 Current Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| No automatic retry on errors | User must manually re-run on failure | Re-run script after resolving error |
| No rate limit handling | Script fails if rate limit hit | Wait 1 hour, then retry |
| Manual S3 upload required | Two-step process | Use AWS CLI for upload |
| No progress bar for large exports | Unclear if long request is working | Add in future version |
| Single date range per execution | Multiple runs needed for multi-year exports | Run script multiple times |

### 9.2 Future Enhancement Ideas

**Priority 1 (High Value):**
- [ ] Add progress indicator for API requests
- [ ] Basic retry logic for transient failures
- [ ] Validate JSONL output format
- [ ] Display estimated file size before export

**Priority 2 (Nice to Have):**
- [ ] Automatic date range splitting for multi-year exports
- [ ] Optional direct S3 upload (if AWS credentials provided)
- [ ] Export multiple date ranges in batch mode
- [ ] Resume partial exports on failure

**Priority 3 (Advanced Features):**
- [ ] Event filtering by event name or properties
- [ ] Compression option (for storage, decompress before PostHog import)
- [ ] Data validation and quality reports
- [ ] Integration with PostHog import API

---

## 10. Security Considerations

### 10.1 Credential Management

**Best Practices:**
- ✓ Store credentials in `.env` file (gitignored)
- ✓ Never commit `.env` to version control
- ✓ Use service account instead of personal credentials
- ✓ Rotate service account secrets regularly

**Risk Mitigation:**
- Credentials never logged to console or files
- `.gitignore` prevents accidental commits
- `.env.example` provides template without secrets

### 10.2 Data Handling

**Sensitive Data:**
- Export files may contain PII (user IDs, emails, etc.)
- Files stored locally on user's machine

**User Responsibilities:**
- Secure local filesystem access
- Delete exports after successful S3 upload
- Secure S3 bucket with appropriate access controls
- Follow data retention policies for exported files

---

## 11. Success Criteria

### 11.1 Functional Success

- [x] Script accepts date range input in YYYY-MM-DD format
- [x] Script validates date ranges correctly
- [x] Script successfully calls Mixpanel Raw Export API
- [x] Script authenticates using Service Account credentials
- [x] Script saves uncompressed JSONL files locally
- [x] Filenames include date range for easy identification
- [x] Files are compatible with PostHog S3 import (Mixpanel content type)

### 11.2 Non-Functional Success

- [x] Script is user-friendly with clear prompts and feedback
- [x] Errors display helpful messages with suggested actions
- [x] Code is maintainable and well-documented
- [x] No hardcoded credentials in source code
- [x] Output files are correctly formatted for PostHog

### 11.3 Acceptance Testing

**Final validation before production use:**
1. ✓ Export 1 month of data successfully
2. ✓ Upload file to S3 manually
3. ✓ Import to PostHog test project
4. ✓ Verify events transformed correctly
5. ✓ Confirm all event properties preserved
6. ✓ Validate timestamps are accurate

---

## 12. Glossary

| Term | Definition |
|------|------------|
| **JSONL** | JSON Lines format - newline-delimited JSON where each line is a valid JSON object |
| **Service Account** | Non-human Mixpanel user for API authentication |
| **Basic Auth** | HTTP authentication using username:password credentials |
| **Raw Export API** | Mixpanel API endpoint for downloading raw event data |
| **PostHog** | Product analytics platform (import destination) |
| **S3** | Amazon Simple Storage Service (file storage for PostHog import) |
| **Distinct ID** | Unique user identifier in Mixpanel/PostHog |
| **Event Properties** | Metadata attached to events (browser, location, custom fields) |
| **Content Type** | S3 metadata indicating data source format (mixpanel/amplitude/posthog) |

---

## 13. References

**Project Documentation:**
- [REQUIREMENTS.md](./REQUIREMENTS.md) - Business requirements
- [mixpanel_api_docs.md](./mixpanel_api_docs.md) - Mixpanel API reference
- [posthog_import_docs.md](./posthog_import_docs.md) - PostHog import guide

**External Documentation:**
- [Mixpanel Raw Export API](https://developer.mixpanel.com/reference/raw-event-export)
- [PostHog Managed Migrations](https://posthog.com/docs/migrate/managed-migrations)
- [Python Requests Library](https://docs.python-requests.org/)
- [AWS CLI S3 Commands](https://docs.aws.amazon.com/cli/latest/reference/s3/)

---

**Document Status:** Ready for Implementation
**Next Steps:** Begin development of `export_mixpanel.py` following this specification
