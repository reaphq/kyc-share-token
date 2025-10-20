# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-20

### Added
- Initial release of KYC Share Token Generator
- Generate share tokens from Sumsub applicant IDs
- Automatic rate limiting (40 requests per 5 seconds)
- Exponential backoff retry mechanism for failed requests
- Resume functionality for interrupted processing
- CSV validation before API calls
- Comprehensive error handling and logging
- Support for custom Sumsub base URLs and client IDs
- Dry-run mode for testing without API calls
- Comprehensive test suite with 40+ tests
- Command-line interface with multiple options
- Environment variable configuration
- MIT License

### Features
- **Core Functionality**:
  - Generate share tokens from CSV input
  - Process up to 40 records per 5 seconds
  - Handle network errors with automatic retries

- **Reliability**:
  - Resume from last successful record
  - Validate CSV format before processing
  - Log errors to output CSV for review

- **Flexibility**:
  - Custom rate limiting
  - Custom Sumsub endpoints
  - Dry-run mode for testing

- **Testing**:
  - 40+ comprehensive unit tests
  - Mock API testing
  - Rate limiting tests
  - Error handling tests

### Documentation
- Comprehensive README with examples
- Integration guide for Reap KYC Batch Upload API
- Contributing guidelines
- Setup and publishing guide
- Example input/output CSV files

## [Unreleased]

### Planned Features
- Parallel processing for faster throughput
- Progress bar for large files
- Detailed error reporting per record
- Support for additional KYC providers
- Configuration file support
- Docker containerization
- GitHub Actions CI/CD pipeline

---

For more details, see the [README](README.md) and [documentation](docs/).
