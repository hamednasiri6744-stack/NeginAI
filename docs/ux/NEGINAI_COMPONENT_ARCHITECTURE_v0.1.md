# NeginAI Component Architecture v0.1

Status:
Draft / Design Foundation

Date:
2026-09-07

---

# 1. Purpose

This document defines the component architecture of NeginAI.

The goal is to create a unified component language between:

- Figma Design System
- Frontend Implementation
- Product Experience

All components must be:

- Reusable
- Consistent
- Responsive
- Accessible
- Token Driven

---

# 2. Component Architecture Principles

## Design System First

No important UI element should be created as an isolated element.

Every component belongs to a structured hierarchy:

Foundation

↓

Primitive Components

↓

Business Components

↓

Experience Patterns

↓

Application Screens

---

## Single Source of Truth

Component definitions must remain synchronized between:

Figma

↓

Design Tokens

↓

Frontend Components

↓

Visual QA

---

## Variant Driven

Components must support defined states and variants.

Examples:

- Default
- Active
- Disabled
- Loading
- Error
- Success

---

## Responsive By Design

Every component must support:

- Mobile
- Tablet
- Desktop

Desktop is an extension of the mobile experience.

---

# 3. Component Layers

NeginAI component architecture:

Foundation

↓

Primitive Components

↓

Business Components

↓

Experience Patterns

↓

Application Screens

---

# 4. Foundation Layer

Foundation defines the visual language.

Includes:

## Color System

- Brand Colors
- Semantic Colors
- Status Colors
- Background Layers

---

## Typography

Text hierarchy:

- Display
- Heading
- Body
- Caption
- Label

---

## Spacing System

Token based spacing:

- XS
- SM
- MD
- LG
- XL

---

## Shape System

Includes:

- Border Radius
- Border
- Shadow
- Glass Effects

---

## Motion System

Includes:

- Transition
- Feedback Animation
- Micro Interaction

---

# 5. Primitive Components

Basic reusable interface elements.

---

# Button

Variants:

- Primary
- Secondary
- Ghost
- Danger
- AI Action

States:

- Default
- Hover
- Active
- Loading
- Disabled

---

# Input

Types:

- Text
- Search
- Filter
- Command Input

States:

- Empty
- Filled
- Error
- Disabled

---

# Card

Used for:

- Information
- KPI
- Action
- AI Insight

Variants:

- Standard Card
- Glass Card
- Interactive Card

---

# Badge

Used for:

- Status
- Category
- Notification

---

# Avatar

Used for:

- User
- Employee
- Agent
- Role

---

# Icon

Rules:

- Consistent icon family
- Accessible labels
- Token controlled sizing

---

# 6. NeginAI Shell Components

The Shell defines the application experience.

Structure:

AppShell

├── BrandHeader

├── ContextBar

├── MainWorkspace

├── AIAction

└── BottomDock

---

# BrandHeader

Purpose:

Provide product identity and global context.

Contains:

- Logo
- Product identity
- User context
- Global actions

---

# ContextBar

Purpose:

Display operational context.

Contains:

- Current role
- Business context
- Location
- Task state
- Filters

---

# MainWorkspace

Primary working area.

Contains:

- Business content
- Data views
- Actions
- Results

---

# AIAction

Persistent AI operational layer.

Provides:

- Suggestions
- Insights
- Explanations
- Next Actions

AI is part of workflow.

---

# BottomDock

Primary mobile navigation.

Contains:

- Home
- AI
- Operations
- Analytics
- More

---

# 7. Business Components

Domain reusable components.

---

# Customer Card

Contains:

- Customer identity
- Sales status
- Credit status
- AI insights
- Actions

---

# Order Card

Contains:

- Order status
- Items
- Approval state
- Actions

---

# Route Card

Contains:

- Route information
- Customers
- Progress
- AI suggestions

---

# KPI Card

Contains:

- Metric
- Trend
- Explanation
- Action

---

# AI Insight Card

Contains:

- Insight
- Confidence
- Explanation
- Recommended action

---

# 8. Experience Patterns

Patterns combine multiple components.

---

## Operational Overview

Combination of:

- KPI Cards
- AI Insights
- Actions

---

## Daily Workflow

Combination of:

- Tasks
- Notifications
- Business Cards
- AI Guidance

---

## Decision Workspace

Combination of:

- Analytics
- Context
- Recommendations
- Execution Actions

---

# 9. Figma Mapping Requirements

Every production component must define:

- Component Name
- Variants
- Properties
- Tokens
- Responsive Rules
- Frontend Mapping

---

# 10. Frontend Mapping

Architecture:

Figma Component

↓

React Component

↓

Design Tokens

↓

Runtime UI

---

Example:

Figma:

NeginAI/Button

Frontend:

<Button />

---

# 11. Component Approval Criteria

A component is approved only when:

- Visual design approved
- Responsive behavior tested
- Accessibility checked
- Token usage confirmed
- Frontend mapping completed

---

# End