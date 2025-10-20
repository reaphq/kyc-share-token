# Contributing to KYC Share Token Generator

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How to Contribute](#how-to-contribute)
3. [Development Setup](#development-setup)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Pull Request Process](#pull-request-process)
7. [Commit Message Guidelines](#commit-message-guidelines)

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

- Be respectful and inclusive
- Welcome constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**Good bug reports include**:
- Clear, descriptive title
- Detailed steps to reproduce
- Expected behavior vs actual behavior
- Environment details (Python version, OS, etc.)
- Error messages and stack traces
- Sample CSV files (if applicable)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:
- Clear description of the enhancement
- Rationale for why it would be useful
- Possible implementation approach
- Examples of how it would be used

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Add tests** for your changes
5. **Run the test suite** to ensure nothing breaks
6. **Commit your changes** (see commit guidelines below)
7. **Push to your fork** (`git push origin feature/amazing-feature`)
8. **Open a Pull Request**

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/kyc-share-token.git
cd kyc-share-token

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your test credentials

# Run tests to verify setup
python test_sumsub_share_token_generator.py
```

### Project Structure

```
kyc-share-token/
├── sumsub_share_token_generator.py  # Main script
├── test_sumsub_share_token_generator.py  # Test suite
├── requirements.txt                  # Python dependencies
├── README.md                        # Project documentation
├── CONTRIBUTING.md                  # This file
├── CHANGELOG.md                     # Version history
├── LICENSE                          # MIT license
├── .env.example                     # Environment template
├── .gitignore                       # Git ignore rules
├── examples/                        # Example files
│   ├── sample_input.csv
│   ├── sample_output.csv
│   └── README.md
├── docs/                           # Additional documentation
│   ├── INTEGRATION.md
│   └── README.md
└── .github/
    └── workflows/
        └── test.yml                 # CI/CD pipeline
```

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with a few exceptions:

- **Line length**: 120 characters (instead of 79)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Use single quotes for strings (unless double quotes avoid escaping)

### Code Style Rules

**1. Naming Conventions**
```python
# Good
def generate_share_token(applicant_id):
    max_retries = 3
    API_BASE_URL = "https://api.sumsub.com"

# Bad
def GenerateShareToken(applicantID):
    maxRetries = 3
    api_base_url = "https://api.sumsub.com"
```

**2. Function Documentation**
```python
def generate_share_token(applicant_id, applicant_level):
    """
    Generate a share token for a Sumsub applicant.

    Args:
        applicant_id (str): Sumsub applicant identifier
        applicant_level (str): Verification level (e.g., 'levelKyc')

    Returns:
        dict: Response containing shareToken and forClientId

    Raises:
        requests.RequestException: If API call fails after retries
        ValueError: If applicant_id or applicant_level is invalid
    """
    pass
```

**3. Error Handling**
```python
# Good - Specific exception handling
try:
    response = requests.post(url, headers=headers)
    response.raise_for_status()
except requests.HTTPError as e:
    logger.error(f"HTTP error: {e}")
    raise
except requests.RequestException as e:
    logger.error(f"Request failed: {e}")
    raise

# Bad - Bare except
try:
    response = requests.post(url, headers=headers)
except:
    pass
```

**4. Type Hints**
```python
# Good - Use type hints
def process_csv(input_file: str, output_file: str) -> int:
    """Process CSV file and return number of records processed."""
    pass

# Acceptable - Type hints not required for simple functions
def is_valid_uuid(value):
    """Check if value is a valid UUID."""
    pass
```

### Import Organization

```python
# Standard library imports
import os
import sys
import time
from typing import List, Dict, Optional

# Third-party imports
import requests
import pandas as pd

# Local application imports
from utils import validate_csv
```

## Testing Guidelines

### Running Tests

```bash
# Run all tests
python test_sumsub_share_token_generator.py

# Run specific test class
python test_sumsub_share_token_generator.py TestCSVValidation

# Run with verbose output
python test_sumsub_share_token_generator.py -v
```

### Writing Tests

**1. Test Organization**
- Group related tests in classes
- Use descriptive test names
- Follow AAA pattern: Arrange, Act, Assert

```python
class TestShareTokenGeneration(unittest.TestCase):
    def test_generate_token_success(self):
        # Arrange
        applicant_id = "test123"
        expected_token = "eyJhbGci..."

        # Act
        result = generate_share_token(applicant_id)

        # Assert
        self.assertEqual(result['shareToken'], expected_token)
```

**2. Test Coverage**
- Aim for >80% code coverage
- Test both success and failure cases
- Test edge cases and boundary conditions
- Mock external API calls

**3. Test Data**
```python
# Use realistic test data
VALID_APPLICANT_ID = "68c276d1827b5c7a72ec620e"
VALID_EXTERNAL_ID = "ef88fd57-26cf-415d-a112-941732c55350"
VALID_APPLICANT_LEVEL = "levelKyc"

# Use fixtures for complex data
@classmethod
def setUpClass(cls):
    cls.sample_csv_data = pd.DataFrame({
        'applicantId': [VALID_APPLICANT_ID],
        'externalId': [VALID_EXTERNAL_ID],
        'applicantLevel': [VALID_APPLICANT_LEVEL]
    })
```

## Pull Request Process

### Before Submitting

1. **Update documentation** if you changed functionality
2. **Add tests** for new features
3. **Run the test suite** and ensure all tests pass
4. **Update CHANGELOG.md** with your changes
5. **Follow commit message guidelines** (see below)

### PR Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
Describe the tests you ran to verify your changes.

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have added tests that prove my fix/feature works
- [ ] All new and existing tests pass
- [ ] I have updated the documentation accordingly
- [ ] I have updated CHANGELOG.md
```

### Review Process

1. At least one maintainer must review and approve
2. All CI checks must pass
3. No merge conflicts
4. Changes must be squashed or rebased before merge

## Commit Message Guidelines

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, missing semi-colons, etc.)
- **refactor**: Code refactoring without changing functionality
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, build config, etc.)

### Examples

```bash
# Good commit messages
feat(generator): add support for custom rate limiting
fix(csv): handle UTF-8 BOM in input files
docs(readme): update installation instructions
test(rate-limit): add tests for exponential backoff

# Bad commit messages
update
fixed bug
changes
WIP
```

### Scope

Common scopes:
- `generator` - Share token generation logic
- `csv` - CSV processing and validation
- `api` - Sumsub API integration
- `rate-limit` - Rate limiting functionality
- `tests` - Test suite
- `docs` - Documentation
- `ci` - CI/CD pipeline

## Questions?

If you have questions about contributing, please:
1. Check existing documentation
2. Search existing issues
3. Open a new issue with the "question" label

---

Thank you for contributing to KYC Share Token Generator!
