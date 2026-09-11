# NeginAI Design System Foundations v0.1

Status:
Draft / Design Foundation

Date:
2026-09-07

---

# 1. Purpose

NeginAI Design System is the visual and interaction foundation for the entire NeginAI Enterprise Operational AI Platform.

The Design System defines:

- Visual language
- Interface consistency
- Component behavior
- Brand expression
- Token architecture
- Figma source of truth
- Frontend implementation rules

The Design System is not a collection of screens.

It is the foundation layer between:

Brand Identity
↓
Figma Variables / Components
↓
Frontend Components
↓
Product Experience

---

# 2. Design Philosophy

NeginAI visual direction:

Modern Enterprise
+
Controlled Glassmorphism
+
Soft Neumorphism

Ratio:

- 70% Clean Enterprise
- 20% Mild Glassmorphism
- 10% Soft Neumorphism

The interface must remain:

- Professional
- Trustworthy
- Operational
- Clear
- Fast
- Accessible

Avoid:

- Gaming appearance
- Excessive glow
- Heavy gradients
- Decorative complexity
- Generic admin dashboard style

---

# 3. Design Principles

## Clarity First

Information hierarchy has priority over decoration.

Every visual element must answer:

- What is this?
- Why is it important?
- What action is available?

---

## Consistency

All products, modules and roles use the same design language.

Differences are created through:

- Permission
- Data visibility
- Available actions

Not different visual systems.

---

## Functional Beauty

Every visual decision must improve:

- Understanding
- Decision making
- Execution speed

---

## AI Native Experience

AI elements must feel integrated into workflows.

AI is represented as:

- Assistant
- Insight provider
- Recommendation engine
- Action accelerator

Not only chat interface.

---

# 4. Design Tokens

Tokens are the single source of truth.

Structure:

Foundation Tokens

↓

Semantic Tokens

↓

Component Tokens

↓

Screen Usage

---

# 5. Color System

## Brand Colors

Primary:

NeginAI Primary

Purpose:

- Main actions
- Brand identity
- Important states


Secondary:

NeginAI Secondary

Purpose:

- Supporting actions
- Highlights


Accent:

AI Accent

Purpose:

- AI related interactions
- Intelligence indicators


---

## Surface Colors

Background:

Enterprise dark/light adaptable surface.

Surface:

Cards and containers.

Elevated Surface:

Dialogs, floating panels and important workspace areas.

---

## Semantic Colors

Success:

Completed operations.

Warning:

Attention required.

Danger:

Critical problems.

Info:

Neutral information.

---

# 6. Typography System

Typography must support:

- Persian RTL
- English
- Enterprise readability
- Dense information environments


Hierarchy:

## Display

Large strategic information.

## Heading

Page and section titles.

## Body

Normal content.

## Caption

Secondary information.

## Data Text

Tables, KPIs and operational numbers.


Typography requirements:

- High readability
- Clear weight hierarchy
- Consistent line height

---

# 7. Spacing System

Spacing follows a token based scale.

Base unit:

4px


Examples:

xs:
4px

sm:
8px

md:
16px

lg:
24px

xl:
32px

2xl:
48px

3xl:
64px


No arbitrary spacing values.

---

# 8. Radius System

Rounded surfaces are part of NeginAI identity.

Tokens:

Small:

8px

Medium:

12px

Large:

20px

Extra Large:

28px


Cards and workspace containers should use consistent radius.

---

# 9. Shadow System

Shadows must be subtle.

Purpose:

- Depth
- Hierarchy
- Separation


Avoid:

- Strong shadows
- Artificial 3D effect


Levels:

Low:

Cards

Medium:

Floating panels

High:

Dialogs

---

# 10. Glassmorphism Rules

Glass effects are controlled.

Allowed:

- Workspace overlays
- AI panels
- Floating actions
- Important navigation surfaces


Rules:

- Low opacity
- High readability
- Minimal blur
- Never hide information


Glass is a functional layer, not decoration.

---

# 11. Soft Neumorphism Rules

Used only for:

- Interactive controls
- AI actions
- Special states


Rules:

- Very subtle depth
- Maintain accessibility contrast
- Never replace normal UI hierarchy


---

# 12. Motion System

Motion communicates state.

Allowed:

- Transition
- Loading
- State change
- AI response

Avoid:

- Continuous animation
- Distracting effects


Motion principles:

Fast

Predictable

Purposeful

---

# 13. Responsive Foundation

Mobile First.

Supported:

- Mobile
- Tablet
- Desktop


Desktop is an extension of mobile experience.

Not a separate product.

---

# 14. RTL Foundation

NeginAI supports Persian RTL as a primary experience.

Requirements:

- Correct direction
- Mirrored navigation
- Logical icon placement
- Proper data alignment


RTL must be considered at component level.

---

# 15. Accessibility Foundation

All components must support:

- Clear contrast
- Keyboard accessibility
- Readable typography
- Clear states
- Screen adaptability


Accessibility is part of quality.

---

# 16. Component Relationship

Design System hierarchy:

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

# 17. Figma Implementation Rules

Figma must be the Visual Source of Truth.

Required:

- Variables
- Tokens
- Styles
- Components
- Variants
- Auto Layout
- Responsive constraints


Mapping:

Figma Component

↓

Frontend Component

↓

Runtime Validation


---

# 18. Frontend Implementation Rules

Frontend must consume Design Tokens.

Avoid:

- Hard coded colors
- Random spacing
- Component duplication


Every major component requires:

- Token mapping
- Responsive behavior
- State definition

---

# 19. Current Status

Version:

v0.1 Draft


Next Steps:

1. Create Token Library
2. Build Figma Foundations
3. Create Component Library
4. Validate with Screens
5. Connect to React Implementation
