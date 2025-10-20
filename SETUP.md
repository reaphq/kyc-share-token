# Publishing Guide - KYC Share Token Generator

This guide provides step-by-step instructions for publishing this repository to GitHub.

## Prerequisites

- Git installed and configured
- GitHub account
- SSH key configured with GitHub (or use HTTPS)
- Repository created at: https://github.com/reaphq/kyc-share-token

## Step 1: Verify Repository Files

Ensure all required files are present:

```bash
# Navigate to repository directory
cd /Users/cyrus/Reap/kyc-share-token

# List all files
ls -la

# Expected files:
# - README.md
# - LICENSE
# - requirements.txt
# - CHANGELOG.md
# - CONTRIBUTING.md
# - SETUP.md (this file)
# - .gitignore
# - .env.example
# - sumsub_share_token_generator.py
# - test_sumsub_share_token_generator.py
# - .github/workflows/test.yml
# - examples/
# - docs/
```

## Step 2: Initialize Git Repository

The repository has already been initialized with the remote origin set to:
```
git@github.com:reaphq/kyc-share-token.git
```

Verify the remote:
```bash
git remote -v
```

Expected output:
```
origin  git@github.com:reaphq/kyc-share-token.git (fetch)
origin  git@github.com:reaphq/kyc-share-token.git (push)
```

## Step 3: Stage All Files

```bash
# Add all files to staging
git add .

# Verify staged files
git status
```

## Step 4: Create Initial Commit

```bash
git commit -m "$(cat <<'EOF'
feat: initial release of KYC Share Token Generator v1.0.0

This release includes:
- Generate share tokens from Sumsub applicant IDs
- Automatic rate limiting (40 requests per 5 seconds)
- Exponential backoff retry mechanism
- Resume functionality for interrupted processing
- CSV validation and error handling
- Comprehensive test suite with 40+ tests
- Full documentation and examples
- MIT License

Features:
- Command-line interface with multiple options
- Support for custom Sumsub base URLs and client IDs
- Dry-run mode for testing
- Integration guide for Reap KYC Batch Upload API

Documentation:
- Comprehensive README with examples
- Integration guide (docs/INTEGRATION.md)
- Contributing guidelines
- Example CSV files
- GitHub Actions CI/CD pipeline
EOF
)"
```

## Step 5: Push to GitHub

```bash
# Push to main branch
git push -u origin master

# If the default branch is 'main' instead of 'master', use:
# git push -u origin main
```

## Step 6: Verify on GitHub

1. Visit: https://github.com/reaphq/kyc-share-token
2. Verify all files are present
3. Check that README.md renders correctly
4. Verify GitHub Actions workflow is configured

## Step 7: Create First Release

### Using GitHub Web Interface

1. Go to: https://github.com/reaphq/kyc-share-token/releases
2. Click "Create a new release"
3. Fill in the release details:
   - **Tag**: `v1.0.0`
   - **Target**: `master` (or `main`)
   - **Release title**: `v1.0.0 - Initial Release`
   - **Description**: Copy from CHANGELOG.md

### Using GitHub CLI (gh)

```bash
# Install GitHub CLI if not already installed
# macOS: brew install gh
# Other: https://cli.github.com/manual/installation

# Authenticate
gh auth login

# Create release
gh release create v1.0.0 \
  --title "v1.0.0 - Initial Release" \
  --notes "$(cat CHANGELOG.md | sed -n '/## \[1.0.0\]/,/## \[Unreleased\]/p' | head -n -2)"
```

## Step 8: Configure Repository Settings

### Topics/Tags

Add relevant topics to help users discover the repository:

1. Go to: https://github.com/reaphq/kyc-share-token
2. Click the gear icon next to "About"
3. Add topics:
   - `python`
   - `kyc`
   - `sumsub`
   - `token-generator`
   - `verification`
   - `csv-processing`
   - `api-integration`
   - `batch-processing`

### Repository Description

Update the repository description:
```
Python CLI tool for generating Sumsub share tokens from CSV data for bulk KYC verification with the Reap API
```

### GitHub Pages (Optional)

If you want to host documentation:

1. Go to Settings > Pages
2. Select source: `Deploy from a branch`
3. Branch: `master` (or `main`), folder: `/docs`
4. Save

## Step 9: Update Links

After publishing, update any placeholder links in the documentation:

1. Update README.md if needed
2. Update docs/INTEGRATION.md if needed
3. Verify all GitHub links work

## Step 10: Test the Published Repository

```bash
# Clone from GitHub to verify everything works
cd /tmp
git clone git@github.com:reaphq/kyc-share-token.git test-clone
cd test-clone

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_sumsub_share_token_generator.py

# Clean up
cd ..
rm -rf test-clone
```

## Post-Publishing Tasks

### 1. Update External-Compliance-Service Documentation

The USER_GUIDE_KYC_BATCH_UPLOAD.md in the external-compliance-service has already been updated with the correct repository link:
```markdown
**Repository**: [`kyc-share-token`](https://github.com/reaphq/kyc-share-token)
```

### 2. Announce the Release

Consider announcing the release:
- Internal team Slack channel
- Developer documentation
- Team meeting

### 3. Monitor Issues and PRs

- Enable GitHub notifications
- Respond to issues promptly
- Review and merge pull requests

### 4. Set Up Branch Protection (Optional)

For collaborative development:

1. Go to Settings > Branches
2. Add rule for `master` (or `main`)
3. Configure:
   - ✓ Require pull request reviews before merging
   - ✓ Require status checks to pass before merging
   - ✓ Require conversation resolution before merging

## Maintenance

### Regular Tasks

- **Update dependencies**: Review and update `requirements.txt` quarterly
- **Security updates**: Monitor for security advisories
- **Documentation**: Keep README and docs up to date
- **Changelog**: Update CHANGELOG.md for each release

### Versioning

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (1.x.x): Breaking changes
- **MINOR** (x.1.x): New features, backwards-compatible
- **PATCH** (x.x.1): Bug fixes, backwards-compatible

### Release Process

For future releases:

```bash
# Update CHANGELOG.md
# Bump version in README.md if needed
# Commit changes
git add .
git commit -m "chore: bump version to vX.Y.Z"

# Create tag
git tag -a vX.Y.Z -m "Release version X.Y.Z"

# Push
git push origin master --tags

# Create GitHub release
gh release create vX.Y.Z --title "vX.Y.Z" --notes "Release notes here"
```

## Troubleshooting

### Issue: Permission denied (publickey)

**Solution**: Ensure SSH key is added to GitHub
```bash
# Generate new SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add to SSH agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Add public key to GitHub
cat ~/.ssh/id_ed25519.pub
# Copy output and add at: https://github.com/settings/keys
```

### Issue: Remote already exists

**Solution**: Remove and re-add remote
```bash
git remote remove origin
git remote add origin git@github.com:reaphq/kyc-share-token.git
```

### Issue: Merge conflicts on push

**Solution**: Pull first, resolve conflicts, then push
```bash
git pull origin master --rebase
# Resolve any conflicts
git push origin master
```

## Additional Resources

- [GitHub Documentation](https://docs.github.com/)
- [Git Documentation](https://git-scm.com/doc)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

**Repository**: https://github.com/reaphq/kyc-share-token

**Maintained by**: Reap Technologies Pte. Ltd.
