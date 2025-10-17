# Mixpanel to PostHog Data Export - Specification

## Overview

Export historical event data from Mixpanel in a format suitable for importing into PostHog via S3. The export will retrieve raw event data from Mixpanel's API and save it as uncompressed JSONL files that PostHog can automatically transform during the import process.

## Approach

1. Use Mixpanel's Raw Data Export API to retrieve event data
2. Accept user-provided date range at runtime (start and end dates)
3. Export all events within the specified date range
4. Save data as uncompressed JSONL files ready for S3 upload
5. User manually handles batching by running multiple exports with different date ranges (respecting PostHog's 1-year import limit)

## Requirements

### Functional Requirements

**FR1: Date Range Input**
- Accept start date and end date as user input when running the export
- Dates should be in YYYY-MM-DD format
- Date range is inclusive of both start and end dates

**FR2: Event Export**
- Export ALL events from Mixpanel (no filtering)
- Include all event properties, distinct_id, and timestamps
- Use millisecond-precision timestamps (time_in_ms=true)

**FR3: Authentication**
- Use Service Account authentication (HTTP Basic Auth)
- Read credentials from environment variables:
  - Service Account Username
  - Service Account Secret
  - Project ID

**FR4: Output Format**
- Save export data as uncompressed JSONL format
- One event per line, each line is valid JSON
- Files must NOT be compressed (.gz, .zip, etc.)
- Ready for PostHog S3 import with automatic Mixpanel transformation

**FR5: File Management**
- Generate descriptive filename with date range (e.g., `mixpanel_export_2024-01-01_to_2024-01-31.jsonl`)
- Save to local directory for subsequent S3 upload

### Technical Requirements

**TR1: API Integration**
- Use Mixpanel Raw Data Export API endpoint: `GET https://data.mixpanel.com/api/2.0/export`
- Required parameters: project_id, from_date, to_date, time_in_ms=true
- Handle JSONL response format

**TR2: Rate Limits (Awareness)**
- Mixpanel API limits: 60 queries/hour, 3 queries/second, max 100 concurrent
- Note: For initial implementation, we're deferring comprehensive error handling

**TR3: Environment Configuration**
- Read credentials from .env file (structure defined in .env.example)
- Required variables:
  - MIXPANEL_SERVICE_ACCOUNT_USERNAME
  - MIXPANEL_SERVICE_ACCOUNT_SECRET
  - MIXPANEL_PROJECT_ID

### Out of Scope (for now)

- Automatic date range batching/splitting
- Data validation and quality checks
- Error handling and retry logic
- S3 upload automation (user will manually upload files)
- Data transformation (using PostHog's automatic transformation)

## Implementation Notes

- User runs export script multiple times with different date ranges to handle PostHog's 1-year import limit
- PostHog will automatically transform Mixpanel event format during S3 import
- Export files should be uploaded to S3 with content type set to "mixpanel"

## Success Criteria

- Script successfully exports all events for user-specified date range
- Output is valid uncompressed JSONL format
- File naming includes date range for easy identification
- Files are compatible with PostHog S3 import (Mixpanel content type)

---

*Last Updated: 2025-10-17*
