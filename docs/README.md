# Networth Tracker Documentation

This directory contains the current setup, operation, security, and development
documentation for Networth Tracker.

## Documentation Structure

### Getting Started
- **[Installation Guide](installation.md)** - Step-by-step installation instructions for all platforms
- **[User Guide](user-guide.md)** - Complete user manual covering all features
- **[Quick Start](quick-start.md)** - Fast track to get up and running
- **[Demo Environment Guide](demo-data.md)** - Explore features with synthetic data in an isolated database

### Deployment and Configuration
- **[Deployment Guide](deployment.md)** - Supported local deployment and operations
- **[Configuration Reference](configuration.md)** - Detailed configuration options
- **[Security Guide](security.md)** - Security best practices and considerations

### Development
- **[Configuration Reference](configuration.md)** - Detailed configuration options for development
- **[Error Handling Guide](error-handling-guide.md)** - Error handling and debugging system
- **[Scripts Reference](scripts/README.md)** - Startup, demo, and utility script behavior
- **[Restart and Process Control](RESTART_USAGE.md)** - PID-based process controls and limitations
- **Source Code**: All source code is included and can be reviewed for development

### Scripts and Utilities
- **Startup Scripts**: `scripts/start.py`, `scripts/start.sh`, `scripts/start.bat`
- **Demo Scripts**: `scripts/generate_demo_database.py`, `scripts/create_demo_backup.py`
- **Database Script Warning**: `scripts/init_db.py` is not compatible with the current database service
- **[Scripts Reference](scripts/README.md)** - Verified commands and known limitations

### Troubleshooting
- **[Error Handling Guide](error-handling-guide.md)** - Error handling and debugging
- **[FAQ](faq.md)** - Frequently asked questions
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

## Quick Navigation

### For New Users
1. Start with the [Installation Guide](installation.md)
2. Follow the [User Guide](user-guide.md) to learn the features
3. Use the [Demo Environment Guide](demo-data.md) to explore with sample data
4. Check the [FAQ](faq.md) for common questions

### For Developers
1. Review the [Configuration Reference](configuration.md)
2. Study the [Error Handling Guide](error-handling-guide.md)
3. Examine the source code structure and patterns

### For Local Operators
1. Review the [Deployment Guide](deployment.md)
2. Study the [Security Guide](security.md)
3. Set up full-database backup procedures

## Documentation Standards

This documentation follows these standards:
- **Markdown Format**: All documentation uses Markdown for consistency
- **Clear Structure**: Hierarchical organization with table of contents
- **Code Examples**: Practical examples for all procedures
- **Cross-Platform**: Instructions for Windows, macOS, and Linux
- **Version Control**: Documentation is versioned with the application

## Contributing to Documentation

When updating documentation:
1. Follow the existing structure and style
2. Include practical examples
3. Test changed procedures on the relevant platforms
4. Update cross-references when adding new sections
5. Keep the main README.md updated with new documents

## Support

If you need help with the documentation:
1. Check the specific guide for your use case
2. Review the troubleshooting sections
3. Look for similar issues in the FAQ
4. Check the error handling guide for technical issues

---

**Application Version**: 1.0.0
**Documentation Last Updated**: 2026-08-22
