# VoiceShield

**AI-Powered Real-Time Detection & Prevention of Voice Cloning Impersonation Attacks**

Smart India Hackathon 2026 — SIH26104
Organization: AICTE | Category: Software | Theme: Blockchain & Cybersecurity

---

## Overview

VoiceShield is a real-time, multi-layered defense system against synthetic voice (deepfake / voice-cloning) impersonation attacks on calls, IVRs, and voice-authenticated transactions.

Unlike single-model passive detectors — which collapse under channel compression and adversarial attack — VoiceShield combines:

1. **A multi-view ensemble spoof-detection model** (waveform + spectrogram + self-supervised branches) for passive, always-on screening.
2. **An active liveness challenge-response layer**, adapted from face-liveness research into the audio domain, for high-risk moments.
3. **An adversarial-robust fusion strategy** that eliminates the "single point of failure" weakness found in single-architecture detectors.
4. **A permissioned blockchain audit layer** giving every detection decision a tamper-proof, independently verifiable trail.
5. **An explainability (XAI) layer** so every flagged call comes with a human-readable reason, not a black-box score.

---

## The Problem

Voice cloning technology has made it trivial to convincingly impersonate a real person's voice from just a few seconds of reference audio. This powers a growing wave of fraud: fake bank officials, fake relatives in distress, fake "digital arrest" calls from law enforcement impersonators, and extortion calls fabricating a loved one's voice.

Existing tools don't close this gap:

- **Caller-ID apps** (Truecaller) verify the number, not the voice.
- **Telecom-network AI** flags calling patterns, not audio content.
- **CNAP** verifies KYC identity, not whether the voice on the line is genuine.
- **Chakshu / cybercrime helplines** act after the call, not during it.

VoiceShield is the missing layer: real-time verification that the voice on an active call is genuinely the person it claims to be — and importantly, this covers more than financial fraud. The same cloning technique drives fake-kidnapping calls, extortion, and harassment, where no money ever changes hands but real psychological harm occurs. VoiceShield's design treats this as a first-class scenario, not an edge case.

---

## System Architecture
```
CLIENT / EDGE LAYER
Mobile SDK · Browser Extension · Telecom SIP/RTP Plugin · IVR/Call-Center Connector
│ live audio stream (WebRTC/RTP)
▼
INGESTION & PREPROCESSING
VAD → chunking (1–4s sliding windows) → noise/codec normalization
▼
FEATURE EXTRACTION
Raw waveform │ LFCC/CQT spectrogram │ SSL embedding (WavLM/wav2vec2)
▼
MULTI-VIEW ENSEMBLE DETECTION (core model)
RawNet2 branch │ ResNet2D/LCNN branch │ SSL branch
→ attention-based fusion → risk score
→ cross-branch agreement gate (adversarial robustness)
▼
RISK DECISION ROUTER
real → continue │ unverified → challenge │ suspected clone → challenge │ speaker-mismatch → challenge
│ │
▼ ▼
LIVENESS CHALLENGE MODULE EXPLAINABILITY (XAI) LAYER
▼ ▼
ALERT & RESPONSE ORCHESTRATOR
block/mute · step-up auth · notify user/bank/SOC · incident ticket
▼
BLOCKCHAIN AUDIT & CONSENT LEDGER
hash of decision, evidence metadata, enrollment consent
▼
ANALYST DASHBOARD & REPORTING API
```

### Key design decisions

- **Two-stage detection.** Stage A determines whether speech is synthetic at all. Stage B checks whether the live voice matches the claimed speaker's enrolled voiceprint. A call can pass Stage A and still fail Stage B — the exact pattern of an attacker cloning a *different* real person's voice to impersonate someone the victim trusts.
- **Open-set fallback.** The system never forces a binary real/fake decision. Genuinely low-confidence audio is explicitly labeled `"unverified"` and routed to a liveness challenge, rather than defaulting to a confident wrong guess.
- **Cross-branch agreement gate.** When the three detection branches strongly disagree — a signature of an adversarial attack tuned against only one architecture — the sample is automatically escalated to a live challenge instead of trusted on the ensemble score alone.
- **Verified-callback pattern.** No third-party app on stock Android/iOS can access a live cellular call's audio once it's answered. For a stranger calling a personal number, VoiceShield offers to place a verified callback through its own VoIP session — audio the system genuinely controls — so full detection still runs.

---

## Detection Model

VoiceShield's core detector is a multi-view ensemble that fuses three independent representations of the same audio:

- **RawNet2** — end-to-end raw waveform branch
- **ResNet2D/LCNN over LFCC/CQT spectrograms** — catches spectral synthesis artifacts
- **Self-supervised embeddings (wav2vec2)** — strong cross-language, cross-speaker generalization

These are combined through an attention-based fusion layer that learns how much to trust each branch per input, rather than simple averaging. This architectural diversity is also an adversarial-robustness property: an attack tuned to fool one branch is unlikely to transfer to the others.

**Benchmark results** (ASVspoof2019 LA):

| Metric | Result |
|---|---|
| EER | 2.66% |
| AUC | 0.99 |

**Codec robustness** — measuring detection accuracy after re-encoding through real telephony codecs:

| Condition | EER |
|---|---|
| Clean | 12.23% |
| Opus 16kbps (VoIP) | 12.77% |
| AMR-NB (cellular) | 12.23% |

The model is exported to ONNX for low-latency, edge/CPU-compatible inference, and served via a FastAPI detection endpoint.

---

## Liveness Challenge-Response

For medium- and high-risk moments (large transfers, password resets, ensemble disagreement), VoiceShield issues a live, randomized challenge the caller must pass in real time:

- **Randomized phrase repetition** — a TTS-generated phrase that can't be pre-recorded
- **Prosody/timing probes** — pace, pitch, and pause patterns hard for a real-time voice-conversion pipeline to reproduce under latency pressure
- **Non-speech vocalization challenge** — asking the caller to cough, laugh, or hum; cloning systems are trained on read speech and are characteristically bad at non-verbal sounds
- **Semantic/compositional challenge** — e.g. "say the second word I gave you, then count backwards from seven," verifying a live, attentive human is actually present

Challenges are chained together for high-risk calls, since research on adaptive challenge-response systems shows chained challenges remain effective even against high-compute adaptive adversaries.

---

## Explainability

Every decision comes with a human-readable reason, not a bare confidence number:

- Per-branch contribution to the final score (e.g. "spectrogram branch flagged unnatural harmonic structure in the 2–4kHz band")
- Plain-language translation for non-technical users: "missing natural breathing pauses," "voice doesn't match the enrolled contact"
- Every decision — pass, flag, unverified, or block — is logged with its explanation for audit and regulatory review

---

## Blockchain Audit & Consent Ledger

Every detection decision, its evidence metadata, and its challenge outcome are hashed and written to a permissioned blockchain ledger — never the raw audio itself, preserving privacy while keeping the record tamper-proof and independently verifiable. Voice-enrollment consent is anchored the same way, giving a verifiable compliance trail. This gives dispute resolution real teeth: if a customer disputes a fraud block, the bank can prove the decision wasn't fabricated after the fact.

---

## Panic-Aware Response

Not every impersonation attack targets a payment. VoiceShield's response layer is built for fake-kidnapping, extortion, and harassment calls as much as financial fraud:

- Calm, de-escalating language instead of alarming "FRAUD DETECTED" warnings
- A pre-shared family safe word, verifiable even when the model is uncertain
- Silent trusted-contact escalation (opt-in) so a calmer second party can help verify
- A short guided verification script for someone under panic
- Non-financial reporting paths (cybercrime.gov.in, 1098/181 helplines)
- Post-incident emotional support resources, regardless of whether money was lost

---

## Real-World Deployment Model

VoiceShield operates across four tracks depending on what audio access is actually available:

| Track | Capability |
|---|---|
| Default dialer / CallScreening app | Pre-answer screening and blocking based on number risk |
| In-app / VoIP calls | Full audio pipeline access — complete detection and challenge flow |
| Post-call clip analysis | Users forward a suspicious recording for verdict |
| Telecom-network partnership | Network-level scale, mirroring how carrier-level spam AI already operates |

For a stranger calling a personal number directly, VoiceShield uses the **verified-callback pattern**: the app places a callback through its own VoIP session, giving full detection coverage on audio it actually controls.

Zero-install channels extend reach to users unlikely to install a new app:
- **WhatsApp voice-note bot** — forward a suspicious clip, get a plain-language verdict back
- **Toll-free IVR line** — reachable from any feature phone, running a verified callback and full detection

---

## Technology Stack

| Layer | Technology |
|---|---|
| Real-time audio capture | WebRTC, SIP/RTP integration, Android/iOS native audio APIs |
| Preprocessing | Silero VAD / WebRTC VAD, librosa |
| Feature extraction | LFCC, CQT, WavLM / wav2vec2 (HuggingFace transformers) |
| Detection models | RawNet2, ResNet2D/LCNN, SSL transformer branch, attention fusion (PyTorch) |
| Model serving | FastAPI, ONNX |
| Evaluation | scikit-learn (EER, AUC, FPR-at-threshold) |
| Blockchain | Hyperledger Fabric (permissioned ledger) |
| Databases | PostgreSQL, TimescaleDB, MinIO/S3 |
| Dashboard | React + TypeScript, Tailwind CSS, WebSocket, Recharts |
| Infra | Docker, GitHub Actions CI/CD |

---

## Repository Structure
```
voiceshield/
├── ml/
│ ├── datasets/ # dataset loading and protocol parsing
│ ├── features/ # LFCC, SSL embedding extraction
│ ├── training/ # branch training, fusion, adversarial training
│ ├── evaluation/ # EER, AUC, FPR-at-threshold metrics
│ ├── experiments/ # codec-robustness experiments
│ ├── export/ # ONNX export, model artifacts
│ └── api/ # FastAPI detection service
├── src/ # frontend: live call UI, challenge UI, dashboard, panic-aware UX
├── data/ # datasets
└── docs/ # architecture and research documentation
```

---

## Running the Services

### Docker Compose (Recommended - All 5 Services)

You can launch all 5 VoiceShield microservices with a single command using Docker Compose:

```bash
docker compose up --build
```

This starts:
- **Frontend App**: `http://localhost:5173`
- **ML Detection Service**: `http://localhost:8000` (API Docs: `/docs`)
- **Backend 2 Ingestion Service**: `http://localhost:8002` (API Docs: `/docs`)
- **Blockchain Audit Ledger**: `http://localhost:4000`
- **WhatsApp Bot**: `http://localhost:4001`

### Running ML Detection Service Standalone

```bash
pip install -r requirements.txt

# Place trained model weights at: ml/export/fusion_model_real.pt

uvicorn ml.api.detection_service:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for an interactive API console, or `POST` an audio file to `/detect`:

```json
{
  "branch_scores": { "rawnet2": 0.02, "spectrogram": 0.04, "ssl": 0.01 },
  "fused_score": 0.03,
  "decision": "real",
  "explanation": "Voice matches expected natural speech patterns across all detection branches."
}
```

---

## Contributing

We welcome contributions! Please refer to [CONTRIBUTING.md](file:///c:/VoiceShield/CONTRIBUTING.md) for development setup, code style guidelines, and the pull request workflow.


---

## Competitive Differentiation

| Capability | Truecaller | Telecom AI | CNAP | Chakshu/FRI | Enterprise tools | **VoiceShield** |
|---|---|---|---|---|---|---|
| First-contact, content-based detection | ✗ | ✗ | ✗ | ✗ | ✓ | **✓** |
| Works on live telecom/mobile calls | ID only | Pattern only | ID only | — | ✗ | **✓** |
| Active response during the call | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Distinguishes generic synthetic speech from impersonation of a specific person | ✗ | ✗ | ✗ | ✗ | ✓ | **✓** |
| Honest "unverified" output instead of forced binary | ✗ | ✗ | ✗ | ✗ | unclear | **✓** |
| Covers non-financial harm (harassment, extortion, fake emergencies) | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |

VoiceShield is not a replacement for CNAP or telecom-level AI — it's the missing layer neither of them covers: real-time verification of whether the voice on an active call is genuinely who it claims to be.

---

## Team

| Role | Owns |
|---|---|
| Frontend | Live call UI, challenge prompts, panic-aware UX, analyst dashboard |
| Backend — Detection & ML | Multi-view model, two-stage detection, adversarial robustness, codec-robustness pipeline |
| Backend — Real-Time Pipeline & Response | Streaming ingestion, verified-callback pattern, liveness challenges, alert orchestration |
| Backend — Data, Trust & Integrations | Database, blockchain audit log, auth/consent, WhatsApp bot, complaint-packet generation |

---

## References

- Xue et al., *RTCFake*, ACL Findings 2026
- *Multi-View Collaborative Learning for audio deepfake detection*, AAAI 2025
- *Adversarial Attacks on audio deepfake detection systems*, MSc thesis, Politecnico di Milano
- *GOTCHA*: challenge-response liveness robustness research
- ASVspoof2019 LA dataset

---

## Roadmap

- Federated learning across participating banks/telecoms
- Cross-modal (audio + video) liveness extension for video-call impersonation
- On-device lightweight model for pre-call mobile screening
- Public transparency reporting from the blockchain ledger
- Integration with DoT's Financial Fraud Risk Indicator (FRI)
