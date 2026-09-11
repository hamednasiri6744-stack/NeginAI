# NeginAI UX Architecture v0.1

Status:
Draft / Design Foundation

Date:
2026-09-07

---

# 1. Product Definition

NeginAI is an Enterprise Operational AI Platform.

The product is not:
- Generic Dashboard
- Chatbot Wrapper
- ERP Skin

The product is:

AI-powered operational workspace
for business intelligence, execution and automation.

---

# 2. Experience Principles

## Mobile First

Mobile experience is the primary interaction model.

Desktop expands the same experience.
It is not a separate product.

---

## Shared Shell

All roles use a common application shell.

Role differences are based on:

- Permission
- Visibility
- Available actions

Not separate products.

---

## AI Native

AI is embedded inside workflows.

AI is not an isolated chat page only.

---

## Operational Focus

The UI should help users:

- Understand situation
- Decide
- Execute
- Follow up

---

# 3. Application Shell

NeginAI Shell:

- Brand Header
- Context Area
- Workspace
- AI Entry Point
- Bottom Navigation

Structure:

AppShell

├── BrandHeader

├── ContextBar

├── MainWorkspace

├── AI Action

└── BottomDock


## Shell Principles

### Shared Experience

The shell is the common foundation of all NeginAI experiences.

All modules are rendered inside the same operational workspace.

---

### Context Awareness

The interface should always provide:

- Current role
- Current business context
- Current task state
- Relevant actions

---

### Action Oriented Design

The user should be able to:

- Understand the situation
- Take action
- Review the result

with minimum navigation overhead.

---

### AI as Operational Layer

AI Action is available throughout the workspace.

It provides:

- Suggestions
- Insights
- Explanations
- Next actions

AI is part of the workflow, not a separate destination.

---

# 4. Information Architecture

NeginAI is organized around business capabilities and operational workflows.

The information architecture is designed to support:

- Daily operations
- Business decisions
- AI assistance
- Automation
- Analytics


## Main Navigation Structure

NeginAI

├── Home

├── AI Assistant

├── Operations
│
│   ├── Routes
│   ├── Visits
│   ├── Customers
│   └── Orders


├── Warehouse


├── Analytics & Reports


├── Automation


└── Administration


---

## Navigation Principles

### Capability Based

Navigation represents business capabilities,
not technical modules.


### Progressive Disclosure

Users see relevant capabilities based on:

- Role
- Permission
- Context


### Shared Platform

All capabilities exist inside one unified NeginAI experience.

Different roles do not create separate applications.

---

# 5. Core Screens

Core screens define the main operational experiences of NeginAI.

Screens are designed around user goals,
not technical modules.


---

# Home Command Center

Purpose:

Provide a daily operational overview
and guide the user toward important actions.


Main Areas:

- AI Briefing
- Operational Status
- Critical Alerts
- KPI Snapshot
- Quick Actions
- Recent Activity


---

# AI Assistant

Purpose:

Provide intelligent assistance
inside operational workflows.


Main Capabilities:

- Business Questions
- Data Insights
- Recommendations
- Explanations
- Suggested Actions


AI Assistant is available as:

- Dedicated workspace
- Contextual action layer


---

# Operations

## Routes

Purpose:

Manage field operations and navigation.


Capabilities:

- Route overview
- Active route
- Customer sequence
- Navigation support
- Route performance


## Visits

Purpose:

Support customer visit workflows.


Capabilities:

- Visit planning
- Visit execution
- Visit history
- Visit insights


## Customers

Purpose:

Provide a complete customer workspace.


Capabilities:

- Customer profile
- Customer history
- Orders
- Financial context
- AI insights


## Orders

Purpose:

Support order lifecycle management.


Capabilities:

- Order creation
- Order review
- Order status
- Order history


---

# Warehouse

Purpose:

Provide operational visibility
for inventory activities.


Capabilities:

- Stock overview
- Availability
- Alerts
- Warehouse assistance


---

# Analytics & Reports

Purpose:

Transform operational data
into decisions.


Capabilities:

- KPI monitoring
- Business analysis
- Performance insights
- AI-generated reports


---

# Automation

Purpose:

Enable intelligent business workflows.


Capabilities:

- Workflow automation
- Notifications
- Task execution
- Process monitoring


---

# Administration

Purpose:

Manage platform configuration.


Capabilities:

- Users
- Roles
- Permissions
- System settings

---

# 6. Design System Direction

The NeginAI Design System defines the visual language,
interaction patterns and reusable UI foundations.

The goal is to create a consistent enterprise-grade experience
across all NeginAI products and interfaces.


---

# Visual Identity Principles

NeginAI visual direction:

Modern Enterprise AI Platform


Design balance:

- 70% Clean Enterprise
- 20% Mild Glassmorphism
- 10% Soft Neumorphism


The visual style must remain:

- Professional
- Clear
- Trustworthy
- Operational


Avoid:

- Gaming aesthetics
- Cyberpunk style
- Overly glossy interfaces
- Generic admin dashboards


---

# Design Foundations


## Color System

The color system should support:

- Enterprise credibility
- Data readability
- Operational states
- AI interactions


Color categories:

- Brand Colors
- Surface Colors
- Text Colors
- Semantic Colors
- Data Visualization Colors


---

## Typography

Typography system must support:

- Persian RTL experience
- English content
- Data density
- Accessibility


Requirements:

- Clear hierarchy
- High readability
- Consistent scale


---

## Spacing System

All layouts use a consistent spacing scale.

Spacing defines:

- Component separation
- Content hierarchy
- Screen rhythm


---

## Shape System

The interface uses controlled rounded geometry.

Defined by:

- Border radius
- Cards
- Containers
- Interactive elements


---

## Elevation & Effects

Effects are used carefully.

Includes:

- Shadows
- Glass surfaces
- Blur layers
- Depth hierarchy


Effects must improve:

- Focus
- Context
- Information grouping


---

# Component Strategy

Components are created from:

Foundations

↓

Components

↓

Patterns

↓

Screens


Core components include:

- AppShell
- BrandHeader
- BottomDock
- GlassCard
- ActionButton
- StatusPill
- KpiTile
- DataCard
- Search
- Filter
- Form Controls
- AI Components


---

# Responsive Strategy

NeginAI follows:

Mobile First

Desktop Expansion


Rules:

- Same product experience
- Same information architecture
- Different spatial adaptation


Mobile:

- Bottom navigation
- Touch optimized
- Focused workflows


Desktop:

- Expanded workspace
- More information density
- Multi-column layouts


---

# Figma Design System Structure

The Figma workspace should contain:


00 Principles

01 Foundations

- Colors
- Typography
- Spacing
- Radius
- Effects
- Variables


02 Components

- Navigation
- Cards
- Buttons
- Inputs
- AI Elements


03 Patterns

- Lists
- Dashboards
- Forms
- Workflows


04 App Shell


05 Screens


06 Prototype


07 Dev Handoff

---

# 7. Figma Design System Execution Plan

The Figma workspace is the visual source of truth
for NeginAI design decisions.

Figma is used as:

- Design System Repository
- Component Library
- Prototype Environment
- Design-to-Code Reference


---

# Figma Workspace Structure


## Page 00 — Project Principles

Contains:

- Product vision
- UX principles
- Visual direction
- Design rules


---

## Page 01 — Foundations

Contains:


### Color Tokens

Categories:

- Brand
- Background
- Surface
- Text
- Border
- Semantic states


### Typography Tokens

Contains:

- Font families
- Font sizes
- Font weights
- Line heights


### Spacing Tokens

Contains:

- Base spacing scale
- Layout spacing
- Component spacing


### Shape Tokens

Contains:

- Radius scale
- Border rules


### Effect Tokens

Contains:

- Shadows
- Blur
- Glass layers


---

## Page 02 — Components

Components are built using Foundations.


Core components:

- AppShell
- BrandHeader
- BottomDock
- Navigation Items
- Buttons
- Cards
- Status Indicators
- KPI Components
- AI Components
- Data Components


Each component must define:

- Variants
- States
- Responsive behavior
- Accessibility rules


---

## Page 03 — Patterns

Patterns combine components.


Examples:

- Dashboard sections
- Operational cards
- Data lists
- Search and filter areas
- Workflow panels
- AI recommendation blocks


---

## Page 04 — Application Shell

Defines:

- Mobile shell
- Tablet shell
- Desktop shell


Includes:

- Header behavior
- Navigation behavior
- Workspace rules


---

## Page 05 — Product Screens

Initial screens:


### Home Command Center

### AI Assistant

### Route Workspace

### Customer Workspace

### Order Workspace

### Warehouse Workspace

### Analytics Workspace


---

## Page 06 — Prototype

Contains:

- User flows
- Interaction testing
- Navigation validation


---

## Page 07 — Dev Handoff

Contains:

- Component mapping
- Token mapping
- Frontend notes
- Implementation references


---

# Design System Governance

All new UI elements must follow:

Foundations

↓

Components

↓

Patterns

↓

Screens


No screen should introduce uncontrolled visual elements.

Reusable decisions become system components.
