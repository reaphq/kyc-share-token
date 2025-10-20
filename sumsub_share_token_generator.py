#!/usr/bin/env python3
"""
Sumsub Share Token Generator

This script processes a CSV file containing Sumsub applicant data and generates
share tokens for each applicant by calling the Sumsub API.

Details:
    - Configurable Incremental output dumping (default: every 100 rows) prevents data loss
    - Rate limiting (40 requests/5s) respects Sumsub API limits
    - skips successful entries by checking output file, retries failed ones    
    - Dry-run mode for safe testing without API calls
    - Atomic file operations with temp files to prevent corruption
    - Intelligent retry logic with exponential backoff + jitter

USAGE:
    python sumsub_share_token_generator.py input.csv output.csv
    python sumsub_share_token_generator.py input.csv output.csv --dry-run --batch-size 50

REQUIREMENTS:
    pip install requests pandas

ENVIRONMENT VARIABLES:
    export SUMSUB_APP_TOKEN="your-app-token"
    export SUMSUB_SECRET="your-secret-key"

REQUIRED COLUMNS:
    The input CSV must contain these columns (other columns are ignored):
    - applicantId: Sumsub applicant ID (required, non-empty)
    - externalId: External identifier for tracking (required, non-empty)  
    - applicantLevel: KYC level name (required, non-empty)

SAMPLE DATA:
    Create a CSV file with the following sample data for testing:
    
    applicantId,externalId,creationDate,lastReviewDate,applicantName,applicantEmail,applicantPhoneNumber,applicantCountry,rejectType,rejectLabels,customTags,sourceKey,result,applicantLevel,platform,status,userComment,clientComment
    68c276d1827b5c7a72ec620e,ef88fd57-26cf-415d-a112-941732c55350,2025-09-11 07:14:25,,"Applicant '68c276d1827b5c7a72ec620e'",,,,,,,,"KYC via API",API,init,,
    68c276d1827b5c7a72ec620f,ef88fd57-26cf-415d-a112-941732c55351,2025-09-11 08:15:30,,"Applicant '68c276d1827b5c7a72ec620f'",,,,,,,,"KYC via API",API,init,,

GENERATED OUTPUT CSV FORMAT (comma-separated):
    externalId,shareToken,applicantLevel,applicantId,forClientId,error
    ef88fd57-26cf-415d-a112-941732c55350,eyJhbGciOi...,levelKyc,68c276d1827b5c7a72ec620e,reap.global_116803,
    
    For dry-run mode, successful entries will have shareToken="DRY_RUN" and empty error field.

COMMAND LINE OPTIONS:
    python sumsub_share_token_generator.py input.csv output.csv [options]
    
    Options:
    --dry-run                     # Do not call API; print requests only
    --batch-size N                # Dump to output file every N processed rows (default: 100)
    # Note: Client ID and TTL are hardcoded (reap.global_116803, 21 days)

API ENDPOINT:
    POST /resources/accessTokens/shareToken
    Documentation: https://docs.sumsub.com/reference/generate-share-token

ERROR HANDLING:
    - Missing credentials: Script exits with error
    - File not found: Script exits with error  
    - API failures: Logged and marked as "FAILED" in output
    - Rate limiting: Built-in delays between API calls
    - Logging: Console + sumsub_share_tokens.log file

SECURITY:
    - Uses HMAC-SHA256 authentication as per Sumsub API requirements
    - Credentials stored in environment variables
    - Comprehensive audit logging
"""

import os
import sys
import time
import logging
import requests
import pandas as pd
from typing import Dict, Optional, Tuple, List, Set
import math
import argparse
from collections import deque
from random import uniform
import hashlib
import hmac
import json
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sumsub_share_tokens.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SumsubShareTokenGenerator:
    """Generates share tokens for Sumsub applicants from CSV data."""
    
    # Static configuration - hardcoded values
    FOR_CLIENT_ID = "reap.global_116803"  # REAP Global Client ID
    TTL_SECONDS = 1814400  # 21 days (1814400 seconds)
    SUMSUB_BASE_URL = "https://api.sumsub.com"
    # Level name now comes per-row from CSV
    
    def __init__(self, app_token: str, app_secret: str, base_url: str = "https://api.sumsub.com", dry_run: bool = False):
        self.app_token = app_token
        self.app_secret = app_secret
        self.base_url = base_url.rstrip('/')
        # Configure session with connection pooling and keep-alive
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SumsubShareTokenGenerator/1.0',
            'Connection': 'keep-alive'
        })
        # Configure connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=1,  # Only need 1 pool for Sumsub API
            pool_maxsize=10,     # Max 10 connections in pool
            max_retries=0        # We handle retries ourselves
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        
        self.dry_run = dry_run
        # Sliding window rate limiter: 40 POST requests per 5 seconds
        self._request_timestamps = deque()  # stores monotonic timestamps of recent requests
        self._rate_window_seconds = 5.0
        self._rate_limit_requests = 40  # for safer side
        
        # Cache for string operations and JSON serialization
        self._string_cache: Dict[str, str] = {}
        self._json_cache: Dict[str, str] = {}
        
    def _generate_auth_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Generate Sumsub authentication headers following the exact pattern from TypeScript code."""
        timestamp = str(int(time.time()))
        method_upper = method.upper()
        data_to_sign = timestamp + method_upper + path + body
        
        signature = hmac.new(
            self.app_secret.encode('utf-8'),
            data_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().lower()

        return {
            'X-App-Token': self.app_token,
            'X-App-Access-Ts': timestamp,
            'X-App-Access-Sig': signature,
            'Content-Type': 'application/json'
        }
    
    def generate_share_token(self, applicant_id: str) -> Optional[Dict]:
        """
        Generate a share token for a specific applicant.
        
        Args:
            applicant_id: The Sumsub applicant ID
            
        Returns:
            Dictionary containing token and metadata, or None if failed
        """
        endpoint = f"/resources/accessTokens/shareToken"
        url = f"{self.base_url}{endpoint}"
        
        payload = {
            "applicantId": applicant_id,
            "forClientId": self.FOR_CLIENT_ID,
            "ttlInSecs": self.TTL_SECONDS
        }
        
        # Dry-run: log and return without requiring credentials/signature
        if self.dry_run:
            # Use lazy string formatting for better performance
            if logger.isEnabledFor(logging.INFO):
                logger.info("[DRY-RUN] POST %s payload={'applicantId': '%s', 'forClientId': '%s', 'ttlInSecs': %d}", 
                           url, applicant_id, self.FOR_CLIENT_ID, self.TTL_SECONDS)
            return { 'token': '', 'forClientId': self.FOR_CLIENT_ID }
        
        # JSON serialization for HMAC signature - must match TypeScript JSON.stringify exactly
        body = json.dumps(payload, separators=(',', ':'), sort_keys=False, ensure_ascii=False)
        
        logger.debug(f"JSON Body for HMAC: {body}")
        
        # Additional debug info to compare with TypeScript implementation
        logger.debug(f"Payload object: {payload}")
        logger.debug(f"Endpoint: {endpoint}")
        logger.debug(f"Full URL: {url}")
        
        headers = self._generate_auth_headers('POST', endpoint, body)
        
        try:
            logger.debug(f"Generating share token for applicant: {applicant_id}")
            response = self._post_with_retries(url, payload, headers)
            if response is None:
                return None
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"Successfully generated token for applicant: {applicant_id}")
                return result
            else:
                logger.error(f"Failed to generate token for applicant {applicant_id}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error for applicant {applicant_id}: {str(e)}")
            return None

    def _enforce_rate_limit(self) -> None:
        """Ensure we don't exceed 40 requests per 5 seconds (POST limit)."""
        now = time.monotonic()
        # purge old timestamps
        while self._request_timestamps and (now - self._request_timestamps[0]) > self._rate_window_seconds:
            self._request_timestamps.popleft()

        if len(self._request_timestamps) >= self._rate_limit_requests:
            # time to wait until oldest is out of window
            oldest = self._request_timestamps[0]
            sleep_seconds = self._rate_window_seconds - (now - oldest) + 0.01
            if sleep_seconds > 0:

                if logger.isEnabledFor(logging.INFO):
                    logger.info("Rate limit: sleeping %.2fs to respect 40/5s", sleep_seconds)
                time.sleep(sleep_seconds)
        # record this request timestamp
        self._request_timestamps.append(time.monotonic())

    def _post_with_retries(self, url: str, json_payload: Dict, headers: Dict[str, str]) -> Optional[requests.Response]:
        """POST with rate limiting and retries.

        - Respects 40 POSTs per 5 seconds per Sumsub docs.
        - Retries on 429 and 5xx with exponential backoff and jitter.
        - Honors Retry-After header when present.
        """
        max_retries = 5
        base_backoff = 0.5  # seconds

        for attempt in range(1, max_retries + 1):
            # Rate limit before issuing the request
            self._enforce_rate_limit()
            try:
                # Send JSON as raw data instead of using json parameter
                # This ensures the exact JSON string used for HMAC signature is sent
                json_string = json.dumps(json_payload, separators=(',', ':'), sort_keys=False, ensure_ascii=False)
                response = self.session.post(url, data=json_string, headers=headers, timeout=30)
            except requests.exceptions.RequestException as e:
                # network/timeout errors -> retry with backoff
                logger.warning(f"Network error on attempt {attempt}/{max_retries}: {e}")
                if attempt == max_retries:
                    return None
                sleep_s = base_backoff * (2 ** (attempt - 1)) + uniform(0, 0.25)
                time.sleep(sleep_s)
                continue

            # Success
            if response.status_code < 400:
                return response

            # Retry-able statuses
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt == max_retries:
                    return response
                retry_after_header = response.headers.get('Retry-After')
                if retry_after_header:
                    try:
                        sleep_s = float(retry_after_header)
                    except ValueError:
                        sleep_s = base_backoff * (2 ** (attempt - 1)) + uniform(0, 0.25)
                else:
                    sleep_s = base_backoff * (2 ** (attempt - 1)) + uniform(0, 0.25)
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("Retryable %d on attempt %d/%d. Retry-After: %s | Backoff: %.2fs",
                                 response.status_code, attempt, max_retries, 
                                 retry_after_header or 'n/a', sleep_s)
                time.sleep(sleep_s)
                continue

            # Non-retryable error
            return response

        return None

    
    # --------------- Helpers for modularity/testability ---------------
    def _load_input_csv(self, input_file: str) -> pd.DataFrame:
        logger.info(f"Reading input file: {input_file}")
        required_cols = ['applicantId', 'externalId', 'applicantLevel']
        try:
            df = pd.read_csv(input_file)
            missing = self._validate_columns(df, required_cols)
            if missing:
                logger.error(f"Input file is missing required columns: {missing}")
                raise ValueError(f"Input file is missing required columns: {missing}")
            # Select only required columns for memory efficiency
            return df[required_cols]
        except Exception as e:
            logger.error(f"Failed to read input file '{input_file}': {e}")
            raise

    def _validate_columns(self, df: pd.DataFrame, required_columns: List[str]) -> List[str]:
        present_cols = list(df.columns)
        logger.info(f"Detected columns: {present_cols}")
        missing = [c for c in required_columns if c not in df.columns]
        return missing

    def _load_existing_output(self, output_file: str) -> Tuple[Optional[pd.DataFrame], Dict[str, bool], List[str]]:
        existing_df: Optional[pd.DataFrame] = None
        success_map: Dict[str, bool] = {}
        existing_order: List[str] = []
        if os.path.exists(output_file):
            try:
                existing_df = pd.read_csv(output_file)
                # Vectorized operations for better performance
                ext_ids_clean = existing_df['externalId'].astype(str).str.strip()
                errors_clean = existing_df['error'].fillna('').astype(str).str.strip()
                
                existing_order = ext_ids_clean.tolist()
                
                # Build success map efficiently using vectorized operations
                mask = ext_ids_clean != ''
                valid_ext_ids = ext_ids_clean[mask]
                valid_errors = errors_clean[mask]
                
                # Create success map in one go
                success_map.update(dict(zip(valid_ext_ids, valid_errors == '')))
                logger.info(f"Loaded existing output entries: {len(success_map)}")
            except Exception as e:
                logger.warning(f"Could not read existing output file '{output_file}': {e}")
        return existing_df, success_map, existing_order

    def _should_skip(self, external_id: str, success_map: Dict[str, bool]) -> bool:
        return external_id in success_map and success_map[external_id]

    def _build_success_row(self, external_id: str, applicant_id: str, applicant_level: str, token_result: Dict, is_dry_run: bool) -> Dict:
        return {
            'externalId': external_id,
            'shareToken': 'DRY_RUN' if is_dry_run else token_result.get('token', ''),
            'applicantLevel': applicant_level,
            'applicantId': applicant_id,
            'forClientId': token_result.get('forClientId', self.FOR_CLIENT_ID),
            'error': ''
        }

    def _build_failure_row(self, external_id: str, applicant_id: str, applicant_level: str, message: str) -> Dict:
        return {
            'externalId': external_id,
            'shareToken': 'FAILED',
            'applicantLevel': applicant_level,
            'applicantId': applicant_id,
            'forClientId': self.FOR_CLIENT_ID,
            'error': message
        }

    @staticmethod
    def _fmt_seconds(seconds: float) -> str:
        """Format seconds into human-readable time string."""
        seconds = int(math.ceil(seconds))
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    def _log_progress(self, processed_count: int, total: int, ok: int, fail: int, skip: int, started_at: float, last_progress_log: float) -> float:
        now = time.monotonic()
        if (now - last_progress_log) >= 5.0:
            elapsed = now - started_at
            # Calculate processing rate and ETA for large datasets
            rate = processed_count / elapsed if elapsed > 0 else 0
            remaining = total - processed_count
            eta = remaining / rate if rate > 0 else 0
            
            # Use lazy string formatting for better performance
            if logger.isEnabledFor(logging.INFO):
                logger.info("Progress: %d/%d (%.1f%%) | ok:%d fail:%d skip:%d | Rate: %.1f/s | ETA: %s",
                           processed_count, total, (processed_count/total)*100,
                           ok, fail, skip, rate, self._fmt_seconds(eta) if eta > 0 else "calculating...")
            return now
        return last_progress_log

    def _merge_stable(self, existing_df: Optional[pd.DataFrame], new_rows: List[Dict]) -> pd.DataFrame:
        columns = ['externalId','shareToken','applicantLevel','applicantId','forClientId','error']
        
        if existing_df is None or existing_df.empty:
            # No existing data - return new rows in input file order
            if not new_rows:
                return pd.DataFrame(columns=columns)
            df = pd.DataFrame(new_rows)
            return self._ensure_columns(df, columns)
        
        if not new_rows:
            return self._ensure_columns(existing_df, columns)
        
        # Build lookup map for new/updated rows
        updated_by_ext = {row.get('externalId', ''): row for row in new_rows}
        existing_ext_ids = set(existing_df['externalId'].astype(str).str.strip().tolist())
        
        # Step 1: Process existing rows in their original order
        merged_rows = []
        for _, existing_row in existing_df.iterrows():
            ext_id = str(existing_row.get('externalId', '')).strip()
            if ext_id and ext_id in updated_by_ext:
                # Update in-place: replace existing row with new data
                merged_rows.append(updated_by_ext[ext_id])
            else:
                # Keep existing row unchanged
                merged_rows.append(existing_row.to_dict())
        
        # Step 2: Append truly new externalIds in input file order (preserving order from new_rows)
        for new_row in new_rows:
            ext_id = new_row.get('externalId', '')
            if ext_id and ext_id not in existing_ext_ids:
                merged_rows.append(new_row)
        
        # Create final DataFrame with consistent columns
        if not merged_rows:
            return pd.DataFrame(columns=columns)
        
        final_df = pd.DataFrame(merged_rows)
        return self._ensure_columns(final_df, columns)
    
    def _ensure_columns(self, df: pd.DataFrame, required_columns: List[str]) -> pd.DataFrame:
        """Ensure DataFrame has all required columns efficiently."""
        missing_cols = set(required_columns) - set(df.columns)
        if missing_cols:
            for col in missing_cols:
                df[col] = ''
        return df[required_columns]

    def _incremental_dump(self, existing_df: Optional[pd.DataFrame], new_output_data: List[Dict], 
                         output_file: str, processed_count: int, total_count: int) -> Optional[pd.DataFrame]:
        """
        Incrementally dump processed data to output file.
        Uses atomic write to prevent file corruption.
        
        Returns:
            Updated DataFrame representing current state of output file
        """
        if not new_output_data:
            return existing_df
            
        logger.info(f"💾 Incremental dump: {processed_count}/{total_count} rows processed, writing {len(new_output_data)} new entries...")
        
        try:
            # Merge new data with existing output
            output_df = self._merge_stable(existing_df, new_output_data)
            
            # Atomic write: write to temporary file first, then rename
            temp_file = output_file + '.tmp'
            output_df.to_csv(temp_file, index=False, sep=',')
            
            # Atomic rename (works on most filesystems)
            shutil.move(temp_file, output_file)
                
            logger.debug(f"✅ Successfully dumped {len(new_output_data)} entries to {output_file}")
            
            # Return updated DataFrame for next iteration
            return output_df
            
        except Exception as e:
            logger.error(f"❌ Failed to dump data incrementally: {e}")
            # Don't raise - continue processing, final dump will catch everything
            return existing_df
            
        finally:
            # Clean up temp file if it exists
            temp_file = output_file + '.tmp'
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass

    def process_csv(self, input_file: str, output_file: str, dump_batch_size : int = 100) -> Tuple[int, int]:
        """
        Process the input CSV file and generate share tokens.
        
        Args:
            input_file: Path to input CSV file
            output_file: Path to output CSV file
            dump_batch_size: Number of processed rows after which to dump to file (default: 100)

        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful_count = 0
        failed_count = 0
        skipped_count = 0
        
        try:
            df = self._load_input_csv(input_file)

            # Load existing output (for retry/skip)
            existing_df, existing_success_map, _ = self._load_existing_output(output_file)
            
            # Filter out rows without applicantId (vectorized operation)
            mask = df['applicantId'].notna() & (df['applicantId'].astype(str).str.strip() != '')
            valid_applicants = df[mask]  # No need for copy() since we're not modifying
            logger.info(f"Found {len(valid_applicants)} applicants with valid applicantId")
            logger.info("=" * 60)
            if len(valid_applicants) == 0:
                logger.warning("No valid applicants found in the CSV file")
                return 0, 0
            
            # Prepare output data and progress tracking
            output_data: List[Dict] = []
            processed_ext_ids: Set[str] = set()
            total_applicants = len(valid_applicants)
            processed_count = 0
            last_progress_log = time.monotonic()
            started_at = time.monotonic()
            last_dump_count = 0  # Track when we last dumped to file

            logger.info(f"Incremental dumping enabled: every {dump_batch_size} processed rows")

            # Processing loop starts here
            
            for index, row in valid_applicants.iterrows():
                # Extract and validate required fields - properly handle NaN values
                applicant_id = str(row['applicantId']).strip() if pd.notna(row['applicantId']) else ''
                external_id = str(row['externalId']).strip() if pd.notna(row['externalId']) else ''
                applicant_level = str(row['applicantLevel']).strip() if pd.notna(row['applicantLevel']) else ''
                
                # Validate all required fields at once
                validation_errors = []
                if not applicant_id or applicant_id.lower() == 'nan':
                    validation_errors.append("Missing 'applicantId' value")
                if not external_id or external_id.lower() == 'nan':
                    validation_errors.append("Missing 'externalId' value")
                if not applicant_level or applicant_level.lower() == 'nan':
                    validation_errors.append("Missing 'applicantLevel' value")
                
                if validation_errors:
                    output_data.append(self._build_failure_row(
                        external_id or '', applicant_id, applicant_level, 
                        '; '.join(validation_errors)
                    ))
                    failed_count += 1
                    processed_count += 1
                    last_progress_log = self._log_progress(processed_count, total_applicants, successful_count, failed_count, skipped_count, started_at, last_progress_log)
                    continue
                
                # Skip if already successfully processed in existing output
                if self._should_skip(external_id, existing_success_map):
                    skipped_count += 1
                    processed_count += 1
                    last_progress_log = self._log_progress(processed_count, total_applicants, successful_count, failed_count, skipped_count, started_at, last_progress_log)
                    continue

                processed_ext_ids.add(external_id)

                # Generate share token (or simulate)
                token_result = self.generate_share_token(applicant_id)
                
                if token_result and 'token' in token_result:
                    output_data.append(self._build_success_row(external_id, applicant_id, applicant_level, token_result, self.dry_run))
                    successful_count += 1
                    logger.debug(f"✓ Success: {external_id}")
                else:
                    if self.dry_run:
                        # In dry-run mode, treat as success but with DRY_RUN token
                        output_data.append(self._build_success_row(external_id, applicant_id, applicant_level, {'token': '', 'forClientId': self.FOR_CLIENT_ID}, self.dry_run))
                        successful_count += 1
                        logger.debug(f"✓ Dry-run: {external_id}")
                    else:
                        output_data.append(self._build_failure_row(external_id, applicant_id, applicant_level, 'Token generation failed'))
                        failed_count += 1
                        logger.error(f"✗ Failed: {external_id}")
                
                # Update progress counters and emit progress every ~5 seconds
                processed_count += 1
                last_progress_log = self._log_progress(processed_count, total_applicants, successful_count, failed_count, skipped_count, started_at, last_progress_log)
                
                # Incremental dump: write to file every dump_batch_size processed rows
                if processed_count - last_dump_count >= dump_batch_size:
                    existing_df = self._incremental_dump(existing_df, output_data, output_file, processed_count, total_applicants)
                    last_dump_count = processed_count
                    output_data = []  # Clear processed data to save memory
            
            # Final dump: write any remaining data
            if output_data:  # Only if there's remaining data
                logger.info(f"Writing final output to file: {output_file}")
                output_df = self._merge_stable(existing_df, output_data)
                output_df.to_csv(output_file, index=False, sep=',')
            else:
                logger.info("All data already written via incremental dumps")
            
            logger.info(f"Processing complete. Successful: {successful_count}, Failed: {failed_count}, Skipped: {skipped_count}")
            return successful_count, failed_count
            
        except FileNotFoundError:
            logger.error(f"Input file not found: {input_file}")
            return 0, 0
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
            return successful_count, failed_count


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Generate Sumsub share tokens from CSV data')
    parser.add_argument('input_csv_file_path', help='Input CSV file path')
    parser.add_argument('output_csv_file_path', help='Output CSV file path')
    parser.add_argument('--dry-run', action='store_true', help='Print requests; do not call API')
    parser.add_argument('--batch-size', type=int, default=100, 
                       help='Number of rows to process before dumping to output file (default: 100)')
    
    args = parser.parse_args()
    
    # Get credentials from environment variables
    app_token = os.getenv('SUMSUB_APP_TOKEN')
    app_secret = os.getenv('SUMSUB_SECRET')
    base_url = os.getenv('SUMSUB_BASE_URL', SumsubShareTokenGenerator.SUMSUB_BASE_URL)

    if not app_token or not app_secret:
        logger.error("Missing required environment variables: SUMSUB_APP_TOKEN and SUMSUB_SECRET")
        sys.exit(1)
    
    # Validate input file exists
    if not os.path.exists(args.input_csv_file_path):
        logger.error(f"Input file does not exist: {args.input_csv_file_path}")
        sys.exit(1)
    
    # Create generator and process CSV
    generator = SumsubShareTokenGenerator(app_token, app_secret, base_url, dry_run=args.dry_run)
    
    logger.info("=" * 60)
    logger.info("Sumsub Share Token Generator")
    logger.info("=" * 60)
    logger.info(f"Input file: {args.input_csv_file_path}")
    logger.info(f"Output file: {args.output_csv_file_path}")
    logger.info(f"Client ID: {SumsubShareTokenGenerator.FOR_CLIENT_ID} (hardcoded)")
    logger.info(f"TTL: {SumsubShareTokenGenerator.TTL_SECONDS} seconds (21 days, hardcoded)")
    logger.info(f"Level: from CSV column 'applicantLevel'")
    if args.dry_run:
        logger.info("Mode: DRY-RUN (no API calls will be made)")
    else:
        logger.info("Mode: LIVE (API calls enabled)")
    logger.info("=" * 60)
    
    start_time = time.time()
    successful, failed = generator.process_csv(args.input_csv_file_path, args.output_csv_file_path, args.batch_size)
    end_time = time.time()
    
    logger.info("=" * 60)
    logger.info(f"Processing completed in {end_time - start_time:.2f} seconds")
    logger.info(f"Results: {successful} successful, {failed} failed")
    logger.info("=" * 60)
    
    if failed > 0:
        sys.exit(1)  # Exit with error code if any failed


if __name__ == "__main__":
    main()
