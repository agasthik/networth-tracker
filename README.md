# Networth Tracker

A secure, privacy-first financial portfolio management application that runs locally on your machine. Track your investments across multiple account types with military-grade encryption and complete data privacy.

## 🚀 Quick Start

```bash
# Clone or download the application
git clone <repository-url> networth-tracker
cd networth-tracker

# Set up and start (automated)
./scripts/start.sh  # macOS/Linux
scripts\start.bat   # Windows

# Or manually
python3 -m venv venv
source venv/bin/activate  # macOS/Linux: venv\Scripts\activate on Windows
./venv/bin/pip install -r requirements.txt
./venv/bin/python scripts/start.py
```

Open your browser to `http://127.0.0.1:5000`

## ✨ Key Features

### 🔒 **Privacy & Security First**
- **Local-only storage** - Your data never leaves your computer
- **Military-grade encryption** - AES-256 encryption for all financial data
- **No cloud dependencies** - Works completely offline
- **Zero data collection** - No analytics, tracking, or telemetry

### 💼 **Comprehensive Portfolio Tracking**
- **Multiple Account Types**: CDs, Savings, 401k, Trading, I-bonds
- **Real-time Stock Prices** - Automatic updates for trading accounts
- **Historical Performance** - Track your portfolio growth over time
- **Multi-broker Support** - Manage accounts across different institutions

### 🛠 **User-Friendly Features**
- **Demo Database** - Import realistic synthetic data to explore features
- **Export/Import** - Encrypted backups for data portability
- **Cross-platform** - Windows, macOS, and Linux support
- **Browser-based** - Clean, responsive web interface

## 📸 Dashboard Preview

![Networth Tracker Dashboard](docs/images/Networth-Tracker-Dashboard.jpg)

*The main dashboard provides a comprehensive overview of your portfolio with real-time account summaries, asset allocation charts, and quick stats. The clean, responsive interface makes it easy to track your financial progress across all account types.*

## 📚 Documentation

### Getting Started
- **[Installation Guide](docs/installation.md)** - Step-by-step setup for all platforms
- **[Quick Start Guide](docs/quick-start.md)** - Get running in 5 minutes
- **[User Guide](docs/user-guide.md)** - Complete feature documentation
- **[Demo Database Guide](docs/demo-data.md)** - Explore features with synthetic data

### Configuration & Deployment
- **[Configuration Reference](docs/configuration.md)** - Detailed configuration options
- **[Deployment Guide](docs/deployment.md)** - Production deployment and setup
- **[Security Guide](docs/security.md)** - Security best practices

### Support & Troubleshooting
- **[FAQ](docs/faq.md)** - Frequently asked questions
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions
- **[Scripts Documentation](docs/scripts/README.md)** - Startup and utility scripts

## 🏗 Project Structure

```
networth-tracker/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── scripts/               # Startup and utility scripts
│   ├── start.py          # Main startup script
│   ├── start.sh          # Unix/Linux/macOS launcher
│   ├── start.bat         # Windows launcher
│   └── init_db.py        # Database initialization
├── models/               # Data models and account types
├── services/             # Business logic services
├── templates/            # HTML templates
├── static/              # CSS, JavaScript, and assets
├── docs/                # Comprehensive documentation
├── tests/               # Test suites
├── logs/                # Application logs
├── backups/             # Data backups
└── requirements.txt     # Python dependencies
```

## 🔧 System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 512 MB available memory
- **Storage**: 100 MB free disk space
- **OS**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)

### Recommended
- **Python**: 3.9 or higher
- **RAM**: 1 GB available memory
- **Storage**: 500 MB free disk space (for data and backups)

## 🛡 Security Features

### Data Protection
- **AES-256 Encryption**: All financial data encrypted at rest
- **PBKDF2 Key Derivation**: 100,000 iterations with random salt
- **Master Password**: Single password protects all your data
- **Secure File Permissions**: Database files protected at OS level

### Privacy Guarantees
- **No Cloud Storage**: All data remains on your local machine
- **No External Transmission**: Only stock symbols sent to APIs (no financial data)
- **No Analytics**: Zero telemetry or usage tracking
- **Open Architecture**: Code can be audited for security

### Network Security
- **Localhost Only**: Application binds to 127.0.0.1 only
- **No Remote Access**: Cannot be accessed from other machines
- **Minimal API Usage**: Only stock price lookups (symbols only)

## 🎯 Supported Account Types

| Account Type | Features |
|--------------|----------|
| **Certificate of Deposit (CD)** | Principal, interest rate, maturity tracking |
| **Savings Accounts** | Balance tracking, interest monitoring |
| **401k Retirement** | Balance, employer match, contribution limits |
| **Trading Accounts** | Stock positions, real-time prices, multi-broker |
| **I-bonds** | Purchase amount, inflation adjustments, maturity |

## 🚦 Getting Help

### Support Resources
1. **[FAQ](docs/faq.md)** - Common questions and answers
2. **[Troubleshooting](docs/troubleshooting.md)** - Issue resolution guide
3. **Log Files** - Check `logs/` directory for error details
4. **[Demo Database Guide](docs/demo-data.md)** - Test functionality with synthetic data

## 📄 License

This project is designed for personal financial management with a focus on privacy and security.

## 🤝 Contributing

Contributions are welcome! Please read the documentation for development setup and contribution guidelines.

---

**⚠️ Important Security Note**: This application is designed for personal use on trusted computers. Always use strong master passwords and keep regular backups of your data.