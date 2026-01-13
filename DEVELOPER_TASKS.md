# Competitor Intel: Developer Task Specification

**Document Version:** 1.0  
**Last Updated:** January 13, 2025  
**Target Milestone:** NADA Event Launch (MVP)

---

## Executive Summary

This document provides a comprehensive specification for developers to implement the UI/UX and feature enhancements for the **Competitor Intel** tool. The requirements are derived from recent product strategy meetings and represent the agreed-upon MVP scope for the NADA event launch.

The current repository (`comp_intel`) contains the backend scraping and analysis infrastructure. This specification outlines the frontend development and backend API extensions required to deliver a complete, user-facing product.

---

## Table of Contents

1. [Current System Architecture](#1-current-system-architecture)
2. [MVP Feature Requirements](#2-mvp-feature-requirements)
3. [UI/UX Specifications](#3-uiux-specifications)
4. [Backend API Requirements](#4-backend-api-requirements)
5. [Data Model Updates](#5-data-model-updates)
6. [Integration Requirements](#6-integration-requirements)
7. [Task Breakdown and Priorities](#7-task-breakdown-and-priorities)
8. [Acceptance Criteria](#8-acceptance-criteria)

---

## 1. Current System Architecture

### 1.1 Existing Components

The repository currently contains the following backend components:

| Component | Location | Purpose |
|-----------|----------|---------|
| **DealershipScraper** | `inventory_tool_scraper.py` | Main scraper orchestrator for extracting inventory and detecting tools |
| **ToolDetector** | `dealership_scraper/detectors/tool_detector.py` | Detects 8 dealership tools (payment calculator, APR disclosure, etc.) |
| **InventoryExtractor** | `dealership_scraper/extractors/inventory_extractor.py` | Extracts vehicle inventory data |
| **MarketComparator** | `dealership_scraper/analyses/market_comparator.py` | Compares user dealership against competitors |
| **JobProcessor** | `orchestrator/job_processor_postgres.py` | Orchestrates job workflow with PostgreSQL |
| **Database Models** | `database/models.py`, `database/postgres_models.py` | SQLite and PostgreSQL data models |

### 1.2 Data Flow

```
User Input (URLs) → Job Queue → Scraper → Database → Analysis → Dossier Generation → Email Notification
```

### 1.3 Current Data Structures

**Tool Types Detected:**
1. Payment Calculator
2. APR Disclosure
3. Lease Payment Options
4. Pre-Qualification Tool
5. Trade-In Tool
6. Online Finance Application
7. SRP Payments Shown
8. VDP Payments Shown

**Vehicle Data Points:**
- Year, Make, Model, Trim
- Price, Monthly Payment
- Condition (New, Used, CPO)
- VIN, Stock Number
- Vehicle Type (Sedan, SUV, Truck, etc.)
- Mileage, Drivetrain, Transmission, Fuel Type
- Exterior/Interior Color

---

## 2. MVP Feature Requirements

### 2.1 Core MVP Features (Must Have for NADA)

| Feature | Priority | Description |
|---------|----------|-------------|
| **URL Management UI** | P0 | Interface for users to input/manage up to 4 competitor URLs |
| **Dossier Display** | P0 | Six-column data presentation with host, 4 competitors, and market average |
| **Segmented Data View** | P0 | Inventory/pricing broken down by condition (New/Used/CPO) and type (Trucks/SUVs/Sedans) |
| **Tool Comparison Grid** | P0 | Binary yes/no grid showing which tools each dealer has |
| **Historical Dossiers** | P0 | Archive of past dossiers accessible from dashboard |
| **Ask Why Feature** | P0 | Pre-populated queries for top 10 analysis questions |
| **Weekly Scheduling Display** | P0 | Clear indication that scrapes run every Wednesday at midnight |

### 2.2 Administrative Features (Internal Use)

| Feature | Priority | Description |
|---------|----------|-------------|
| **Admin Scrape Override** | P1 | Ability to trigger on-demand scrapes for pre-event preparation |
| **User Credential Management** | P1 | Create logins for Joe and Charlie to manage URL inputs |

### 2.3 Post-MVP Features (Future Enhancement)

| Feature | Priority | Description |
|---------|----------|-------------|
| **Natural Language Query** | P2 | Allow dealers to query their data with natural language |
| **Make/Model Level Analysis** | P2 | Deeper granularity for specific vehicle comparisons |
| **Expanded Ask Why Questions** | P2 | Growing beyond initial 10-25 questions |

---

## 3. UI/UX Specifications

### 3.1 Application Structure

```
competitor-intel.onekeel.ai/
├── /login                    # SSO redirect
├── /dashboard                # Main dashboard with URL management
├── /dossier/:id              # Individual dossier view
├── /dossier/:id/ask-why/:q   # Ask Why detail view
├── /history                  # Historical dossiers list
└── /admin                    # Admin panel (restricted)
    └── /admin/scrape         # Manual scrape trigger
```

### 3.2 Dashboard Page Specification

**Purpose:** Primary interface for users to manage their competitor analysis setup.

**Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│  COMPETITOR INTEL                              [User Menu] [SSO]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  YOUR DEALERSHIP: [Dealership Name]                             │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  COMPETITOR URLS                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. [URL Input Field]           [Name Input]             │   │
│  │ 2. [URL Input Field]           [Name Input]             │   │
│  │ 3. [URL Input Field]           [Name Input]             │   │
│  │ 4. [URL Input Field]           [Name Input]             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                            [Save Competitors]   │
│                                                                 │
│  ⓘ Analysis runs every Wednesday at midnight                    │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  RECENT DOSSIERS                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Date          │ Status    │ Competitors │ Action        │   │
│  │ Jan 8, 2025   │ Complete  │ 4           │ [View]        │   │
│  │ Jan 1, 2025   │ Complete  │ 4           │ [View]        │   │
│  │ Dec 25, 2024  │ Complete  │ 3           │ [View]        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                            [View All History]   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Functional Requirements:**
- URL fields must validate that input is a valid URL format
- Name fields are required for each URL
- "Save Competitors" button saves all URLs and names to the database
- Users cannot trigger immediate scrapes (display-only schedule indicator)
- Recent dossiers show the last 5 entries; "View All History" links to full list

### 3.3 Dossier View Page Specification

**Purpose:** Display the complete competitive analysis dossier in a structured, actionable format.

**Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│  COMPETITOR INTEL                              [User Menu] [SSO]│
├─────────────────────────────────────────────────────────────────┤
│  ← Back to Dashboard                                            │
│                                                                 │
│  COMPETITIVE ANALYSIS DOSSIER                                   │
│  Generated: January 8, 2025                                     │
│                                                                 │
│  ═══════════════════════════════════════════════════════════════│
│  SECTION 1: WEBSITE TOOL COMPARISON                             │
│  ═══════════════════════════════════════════════════════════════│
│                                                                 │
│  ┌────────────────┬──────┬──────┬──────┬──────┬──────┬────────┐│
│  │ Tool           │ You  │ Comp1│ Comp2│ Comp3│ Comp4│ Market ││
│  ├────────────────┼──────┼──────┼──────┼──────┼──────┼────────┤│
│  │ Payment Calc   │  ✓   │  ✓   │  ✓   │  ✗   │  ✓   │ 80%    ││
│  │ APR Disclosure │  ✗   │  ✓   │  ✓   │  ✓   │  ✓   │ 100%   ││
│  │ Lease Options  │  ✓   │  ✗   │  ✓   │  ✓   │  ✗   │ 50%    ││
│  │ Pre-Qual Tool  │  ✗   │  ✓   │  ✗   │  ✓   │  ✓   │ 75%    ││
│  │ Trade-In Tool  │  ✓   │  ✓   │  ✓   │  ✓   │  ✓   │ 100%   ││
│  │ Online Finance │  ✗   │  ✓   │  ✓   │  ✓   │  ✓   │ 100%   ││
│  │ SRP Payments   │  ✓   │  ✗   │  ✓   │  ✗   │  ✓   │ 50%    ││
│  │ VDP Payments   │  ✓   │  ✓   │  ✓   │  ✓   │  ✓   │ 100%   ││
│  └────────────────┴──────┴──────┴──────┴──────┴──────┴────────┘│
│                                                                 │
│  ═══════════════════════════════════════════════════════════════│
│  SECTION 2: INVENTORY COMPARISON                                │
│  ═══════════════════════════════════════════════════════════════│
│                                                                 │
│  ── NEW VEHICLES ──────────────────────────────────────────────│
│                                                                 │
│  TRUCKS                                                         │
│  ┌────────────────┬──────┬──────┬──────┬──────┬──────┬────────┐│
│  │ Metric         │ You  │ Comp1│ Comp2│ Comp3│ Comp4│ Avg    ││
│  ├────────────────┼──────┼──────┼──────┼──────┼──────┼────────┤│
│  │ Total Count    │  45  │  62  │  38  │  55  │  41  │  49    ││
│  │ Avg Price      │$52K  │$48K  │$55K  │$51K  │$49K  │$50.75K ││
│  │ vs Market      │+2.5% │-5.4% │+8.4% │+0.5% │-3.4% │  --    ││
│  └────────────────┴──────┴──────┴──────┴──────┴──────┴────────┘│
│                                              [Ask Why] ▼        │
│                                                                 │
│  SUVs                                                           │
│  ┌────────────────┬──────┬──────┬──────┬──────┬──────┬────────┐│
│  │ ...            │      │      │      │      │      │        ││
│  └────────────────┴──────┴──────┴──────┴──────┴──────┴────────┘│
│                                              [Ask Why] ▼        │
│                                                                 │
│  SEDANS                                                         │
│  ┌────────────────┬──────┬──────┬──────┬──────┬──────┬────────┐│
│  │ ...            │      │      │      │      │      │        ││
│  └────────────────┴──────┴──────┴──────┴──────┴──────┴────────┘│
│                                              [Ask Why] ▼        │
│                                                                 │
│  ── USED VEHICLES ─────────────────────────────────────────────│
│  [Same structure as above for Trucks, SUVs, Sedans]            │
│                                                                 │
│  ── CPO VEHICLES ──────────────────────────────────────────────│
│  [Same structure as above for Trucks, SUVs, Sedans]            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Functional Requirements:**
- Tool comparison uses checkmarks (✓) and X marks (✗) for binary display
- Market column shows percentage of competitors with each tool
- Inventory sections are collapsible for easier navigation
- "Ask Why" button appears next to each data section
- Percentage differences should be color-coded (green for favorable, red for unfavorable)

### 3.4 Ask Why Feature Specification

**Purpose:** Provide pre-built explanations for common competitive analysis questions.

**Interaction Flow:**
1. User clicks "Ask Why" button next to a data section
2. A modal or expandable panel opens
3. Panel displays a list of pre-populated questions relevant to that section
4. User clicks a question
5. System displays the pre-generated answer/analysis

**MVP Questions (Top 10):**

| # | Question | Applicable Section |
|---|----------|-------------------|
| 1 | Why is my average price higher/lower than competitors? | Inventory Pricing |
| 2 | Why do I have fewer/more vehicles in this category? | Inventory Count |
| 3 | Which specific vehicles are affecting my average price? | Inventory Pricing |
| 4 | Why don't I have this tool on my website? | Tool Comparison |
| 5 | How does my inventory mix compare to the market? | Inventory Overview |
| 6 | Which competitor has the most competitive pricing? | Inventory Pricing |
| 7 | What is driving the price difference in trucks/SUVs/sedans? | Inventory Pricing |
| 8 | How does my CPO inventory compare to competitors? | CPO Section |
| 9 | Which tools are most common among my competitors? | Tool Comparison |
| 10 | What is my competitive position in the market? | Overall Summary |

**UI Component:**

```
┌─────────────────────────────────────────────────────────────────┐
│  ASK WHY: NEW TRUCKS PRICING                              [X]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Select a question:                                             │
│                                                                 │
│  ○ Why is my average price 2.5% higher than the market?         │
│  ○ Which specific trucks are affecting my average price?        │
│  ○ Which competitor has the most competitive truck pricing?     │
│  ○ What is driving the price difference in my truck inventory?  │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ANSWER:                                                        │
│  [Answer content appears here after question selection]         │
│                                                                 │
│  Your average truck price of $52,000 is 2.5% above the market   │
│  average of $50,750. This is primarily driven by:               │
│                                                                 │
│  • 3 high-end trim levels (Raptor, Limited) averaging $78,000   │
│  • Lower inventory count (45 vs market avg 49)                  │
│  • Higher proportion of 2025 model year vehicles                │
│                                                                 │
│  Competitor 1 has the most competitive pricing at $48,000 avg,  │
│  with a larger inventory of 62 trucks.                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5 Admin Panel Specification

**Purpose:** Internal tool for administrators to trigger on-demand scrapes.

**Access Control:** Restricted to users with admin role (Joe, Charlie, internal team).

**Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│  COMPETITOR INTEL - ADMIN                      [Admin] [Logout] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MANUAL SCRAPE TRIGGER                                          │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  User/Dealership: [Search/Select Dropdown]                      │
│                                                                 │
│  [Trigger Scrape Now]                                           │
│                                                                 │
│  ⚠️ Note: Scrapes can take up to 5 hours to complete.           │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  RECENT ADMIN SCRAPES                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ User          │ Triggered By │ Started     │ Status     │   │
│  │ La Fontaine   │ Charlie      │ 10:30 AM    │ Processing │   │
│  │ Kunis Auto    │ Joe          │ Yesterday   │ Complete   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Backend API Requirements

### 4.1 New API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/auth/sso` | GET | Redirect to One Keel SSO | No |
| `/api/auth/callback` | GET | SSO callback handler | No |
| `/api/user/me` | GET | Get current user info | Yes |
| `/api/competitors` | GET | Get user's saved competitors | Yes |
| `/api/competitors` | POST | Save/update competitor URLs | Yes |
| `/api/dossiers` | GET | List user's historical dossiers | Yes |
| `/api/dossiers/{id}` | GET | Get specific dossier data | Yes |
| `/api/dossiers/{id}/ask-why` | GET | Get Ask Why content for dossier | Yes |
| `/api/admin/users` | GET | List all users (admin) | Admin |
| `/api/admin/scrape` | POST | Trigger manual scrape (admin) | Admin |
| `/api/admin/scrapes` | GET | List recent admin scrapes | Admin |

### 4.2 API Response Schemas

**GET /api/competitors Response:**
```json
{
  "competitors": [
    {
      "id": 1,
      "url": "https://competitor1.com",
      "name": "Competitor Dealership 1",
      "last_scraped": "2025-01-08T00:00:00Z"
    }
  ],
  "max_competitors": 4,
  "next_scrape": "2025-01-15T00:00:00Z"
}
```

**GET /api/dossiers/{id} Response:**
```json
{
  "id": "dossier_abc123",
  "generated_at": "2025-01-08T00:00:00Z",
  "host": {
    "name": "User Dealership",
    "url": "https://userdealership.com"
  },
  "competitors": [
    {"name": "Comp 1", "url": "https://comp1.com"},
    {"name": "Comp 2", "url": "https://comp2.com"}
  ],
  "tool_comparison": {
    "payment_calculator": {"host": true, "competitors": [true, true, false, true], "market_pct": 80},
    "apr_disclosure": {"host": false, "competitors": [true, true, true, true], "market_pct": 100}
  },
  "inventory": {
    "new": {
      "trucks": {
        "host": {"count": 45, "avg_price": 52000, "vs_market": 2.5},
        "competitors": [
          {"count": 62, "avg_price": 48000, "vs_market": -5.4},
          {"count": 38, "avg_price": 55000, "vs_market": 8.4}
        ],
        "market_avg": {"count": 49, "avg_price": 50750}
      },
      "suvs": { },
      "sedans": { }
    },
    "used": { },
    "cpo": { }
  },
  "ask_why_available": true
}
```

---

## 5. Data Model Updates

### 5.1 New Database Tables

**users Table:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    dealership_name VARCHAR(255),
    dealership_url VARCHAR(500),
    role VARCHAR(50) DEFAULT 'user',  -- 'user' or 'admin'
    sso_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

**user_competitors Table:**
```sql
CREATE TABLE user_competitors (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    competitor_url VARCHAR(500) NOT NULL,
    competitor_name VARCHAR(255) NOT NULL,
    position INTEGER CHECK (position BETWEEN 1 AND 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, position)
);
```

**dossiers Table:**
```sql
CREATE TABLE dossiers (
    id VARCHAR(50) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    generated_at TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'complete',
    data_path VARCHAR(500),  -- Path to JSON file with full dossier data
    summary JSONB,  -- Quick access summary data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**admin_scrapes Table:**
```sql
CREATE TABLE admin_scrapes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    triggered_by INTEGER REFERENCES users(id),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT
);
```

---

## 6. Integration Requirements

### 6.1 Single Sign-On (SSO) Integration

The application must integrate with the One Keel SSO system (referred to as "Keel Bridge" in discussions).

**Requirements:**
- Redirect unauthenticated users to SSO login page
- Handle SSO callback and create/update local user record
- Store SSO token for session management
- Support role-based access (user vs admin)

**Coordination Required:** Work with Manus team to obtain SSO integration documentation and credentials.

### 6.2 Email Notification Integration

Existing email notification system should be extended to:
- Notify users when their weekly dossier is ready
- Include a direct link to view the dossier
- Optionally include key highlights from the analysis

### 6.3 Scheduling System

**Weekly Scrape Schedule:**
- Scrapes run every Wednesday at midnight
- Users cannot modify this schedule
- Display next scheduled scrape time on dashboard

**Implementation:** Use existing job processing infrastructure with cron-based scheduling.

---

## 7. Task Breakdown and Priorities

### Phase 1: Foundation (Week 1)

| Task ID | Task | Assignee | Priority | Est. Hours |
|---------|------|----------|----------|------------|
| FE-001 | Set up React/Vite project with Tailwind CSS | TBD | P0 | 4 |
| FE-002 | Create basic routing structure | TBD | P0 | 2 |
| FE-003 | Implement login page with SSO redirect | TBD | P0 | 4 |
| BE-001 | Create users table and API endpoints | TBD | P0 | 6 |
| BE-002 | Implement SSO callback handler | TBD | P0 | 8 |
| BE-003 | Create user_competitors table and API | TBD | P0 | 4 |

### Phase 2: Core Features (Week 2)

| Task ID | Task | Assignee | Priority | Est. Hours |
|---------|------|----------|----------|------------|
| FE-004 | Build dashboard page layout | TBD | P0 | 8 |
| FE-005 | Implement competitor URL management form | TBD | P0 | 6 |
| FE-006 | Build historical dossiers list component | TBD | P0 | 4 |
| BE-004 | Create dossiers table and list API | TBD | P0 | 4 |
| BE-005 | Implement dossier detail API with full data | TBD | P0 | 8 |

### Phase 3: Dossier Display (Week 3)

| Task ID | Task | Assignee | Priority | Est. Hours |
|---------|------|----------|----------|------------|
| FE-007 | Build dossier view page layout | TBD | P0 | 8 |
| FE-008 | Implement tool comparison table | TBD | P0 | 4 |
| FE-009 | Implement inventory comparison tables | TBD | P0 | 8 |
| FE-010 | Add collapsible sections and navigation | TBD | P0 | 4 |
| FE-011 | Implement color-coding for metrics | TBD | P0 | 2 |

### Phase 4: Ask Why Feature (Week 4)

| Task ID | Task | Assignee | Priority | Est. Hours |
|---------|------|----------|----------|------------|
| FE-012 | Build Ask Why modal component | TBD | P0 | 6 |
| FE-013 | Implement question selection and answer display | TBD | P0 | 4 |
| BE-006 | Generate Ask Why content during analysis | TBD | P0 | 12 |
| BE-007 | Create Ask Why API endpoint | TBD | P0 | 4 |

### Phase 5: Admin Features (Week 4-5)

| Task ID | Task | Assignee | Priority | Est. Hours |
|---------|------|----------|----------|------------|
| FE-014 | Build admin panel layout | TBD | P1 | 4 |
| FE-015 | Implement manual scrape trigger form | TBD | P1 | 4 |
| FE-016 | Build admin scrape history table | TBD | P1 | 3 |
| BE-008 | Create admin_scrapes table and APIs | TBD | P1 | 6 |
| BE-009 | Implement admin scrape trigger logic | TBD | P1 | 4 |

### Phase 6: Polish and Testing (Week 5)

| Task ID | Task | Assignee | Priority | Est. Hours |
|---------|------|----------|----------|------------|
| QA-001 | End-to-end testing of user flows | TBD | P0 | 8 |
| QA-002 | Cross-browser testing | TBD | P0 | 4 |
| QA-003 | Mobile responsiveness testing | TBD | P1 | 4 |
| FE-017 | Bug fixes and UI polish | TBD | P0 | 8 |
| BE-010 | Performance optimization | TBD | P1 | 6 |

---

## 8. Acceptance Criteria

### 8.1 MVP Launch Criteria

The following must be complete and functional for NADA launch:

- [ ] Users can log in via One Keel SSO
- [ ] Users can view their dashboard with dealership information
- [ ] Users can input and save up to 4 competitor URLs
- [ ] Users can view their most recent dossier
- [ ] Dossier displays tool comparison in grid format
- [ ] Dossier displays inventory comparison by condition and type
- [ ] All data is presented in the six-column format
- [ ] Users can access historical dossiers
- [ ] Ask Why feature works for top 10 questions
- [ ] Admin users can trigger manual scrapes
- [ ] System clearly displays next scheduled scrape time

### 8.2 Quality Standards

- All API endpoints return proper error messages
- UI is responsive on desktop and tablet
- Page load time under 3 seconds
- No critical security vulnerabilities
- All user inputs are validated and sanitized

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Dossier** | The competitive analysis report generated for a dealership |
| **Host** | The user's dealership (the subscriber) |
| **Competitor** | One of up to 4 dealerships the user wants to compare against |
| **Tool** | A website feature like payment calculator, trade-in tool, etc. |
| **Condition** | Vehicle status: New, Used, or CPO (Certified Pre-Owned) |
| **Type** | Vehicle body style: Trucks, SUVs, or Sedans |
| **Ask Why** | Feature that provides pre-built explanations for data points |
| **SSO** | Single Sign-On via One Keel authentication system |

---

## Appendix B: Related Documents

- [Transcript Analysis: COMPETITOR INTEL and Other Products](/home/ubuntu/transcript_analysis.md)
- Original call transcripts (4 files)
- One Keel SSO Integration Guide (to be provided by Manus team)

---

*Document prepared for the Competitor Intel development team. For questions, contact the project lead.*
