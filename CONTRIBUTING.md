# Contributing to VoiceShield

Thank you for your interest in contributing to **VoiceShield**! We welcome contributions from developers, researchers, security enthusiasts, and accessibility advocates.

This document outlines the guidelines and workflow for contributing to the project.

---

## 📜 Table of Contents

1. [Code of Conduct](#-code-of-conduct)
2. [How Can I Contribute?](#-how-can-i-contribute)
   - [Reporting Bugs](#reporting-bugs)
   - [Suggesting Enhancements](#suggesting-enhancements)
   - [Pull Requests](#pull-requests)
3. [Development Setup](#-development-setup)
   - [Option A: Docker Compose (Recommended)](#option-a-docker-compose-recommended)
   - [Option B: Local Manual Setup](#option-b-local-manual-setup)
4. [Project Architecture & Directory Structure](#-project-architecture--directory-structure)
5. [Git Workflow & Commit Guidelines](#-git-workflow--commit-guidelines)
6. [Code Style & Standards](#-code-style--standards)

---

## 🤝 Code of Conduct

We are committed to providing a welcoming, inclusive, and respectful community for everyone. 

- Be respectful and considerate in communications and code reviews.
- Focus on constructive feedback and collaboration.
- Respect privacy — do not share real phone numbers, real identity credentials, or sensitive audio data in issues or PRs.

---

## 💡 How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing open and closed issues to avoid duplicates. When filing a bug report, include:

- A clear and descriptive title.
- A summary of the problem and expected vs. actual behavior.
- Steps to reproduce the bug.
- System details (OS, Python version, Node.js version, browser).
- Relevant stack traces or error logs (sanitize any private tokens/secrets).

### Suggesting Enhancements

We welcome proposals for new features, ML model improvements, active liveness challenges, and UI enhancements!

- Use the GitHub Issue tracker to open a feature request.
- Explain the **use case**, **expected benefits**, and any **architectural implications**.

### Pull Requests

1. **Fork** the repository and create a new branch from `main`.
2. Keep PRs focused on a single concern (e.g. a specific bug fix or feature).
3. Ensure all tests pass and linters report no errors.
4. Update relevant documentation (`README.md`, docstrings, inline comments).
5. Submit your PR with a clear summary of changes and reference any resolved issue numbers (e.g., `Closes #30`).

---

## 🛠️ Development Setup

VoiceShield consists of five interconnected microservices:
1. **Frontend**: Vite + React + Tailwind CSS
2. **ML Service**: FastAPI + PyTorch / ONNX Runtime spoof detection (`port 8000`)
3. **Backend 2 Service**: FastAPI real-time ingestion & risk router (`port 8002`)
4. **Blockchain Service**: Node.js + Express permissioned audit ledger (`port 4000`)
5. **WhatsApp Bot**: Node.js + Express + Twilio webhook (`port 4001`)

### Option A: Docker Compose (Recommended)

To launch all 5 services simultaneously:

```bash
# Clone the repository
git clone https://github.com/aeriellaaa/VoiceShield.git
cd VoiceShield

# Build and start containers
docker compose up --build
```

Access the services:
- **Frontend Dashboard**: `http://localhost:5173`
- **ML Detection Service**: `http://localhost:8000/docs`
- **Backend 2 Ingestion Service**: `http://localhost:8002/docs`
- **Blockchain Audit Ledger**: `http://localhost:4000/health`
- **WhatsApp Bot**: `http://localhost:4001/health`

### Option B: Local Manual Setup

#### Prerequisites
- Node.js >= 18.x
- Python >= 3.10
- `pip` / `uv` package manager

#### 1. Python Dependencies (ML & Backend 2)
```bash
pip install -r requirements.txt
```

#### 2. Frontend
```bash
npm install
npm run dev
```

#### 3. Blockchain Service
```bash
cd blockchain
npm install
node app/index.js
```

#### 4. WhatsApp Bot Service
```bash
cd whatsapp-bot
npm install
node app/index.js
```

#### 5. ML Detection & Backend Services
```bash
# Terminal 1: ML Service
uvicorn ml.api.detection_service:app --reload --port 8000

# Terminal 2: Backend 2 Ingestion Service
uvicorn backend2.backend2_service:app --reload --port 8002
```

---

## 📁 Project Architecture & Directory Structure

```
VoiceShield/
├── src/            # Vite + React frontend (Dashboard, Call Stream, Challenges)
├── ml/             # Machine Learning pipeline & FastAPI detection service
├── backend2/       # Real-time ingestion, risk router & challenge orchestrator
├── blockchain/     # Audit ledger Node.js service
├── whatsapp-bot/   # WhatsApp Twilio bot integration service
├── public/         # Static web assets
├── docker-compose.yml # Container orchestration specification
├── Dockerfile      # Frontend container build specification
└── requirements.txt# Pinned Python dependency manifest
```

---

## 🌿 Git Workflow & Commit Guidelines

We use **Conventional Commits** for clean commit history:

- `feat:` A new feature (e.g., `feat: add ONNX runtime inference`)
- `fix:` A bug fix (e.g., `fix: align MFCC naming in detection pipeline`)
- `docs:` Documentation changes (e.g., `docs: add CONTRIBUTING.md guide`)
- `chore:` Maintenance tasks, dependency updates, configuration changes
- `refactor:` Code refactoring without functionality change
- `test:` Adding or updating tests

### Branch Naming Convention

- `feat/feature-name`
- `fix/issue-description`
- `docs/doc-update-name`
- `chore/maintenance-task`

---

## 🎨 Code Style & Standards

### JavaScript / TypeScript / React
- We use **Oxlint** for fast JS/TS linting (`npm run lint`).
- Follow modern React functional components with hooks.
- Maintain responsive UI design with Tailwind CSS.

### Python
- Follow **PEP 8** style guidelines.
- Use explicit type hints for API contracts.
- Lazy-load heavy ML models / weights where possible.

---

Thank you for helping keep calls safe and fraud-free with **VoiceShield**! 🛡️
