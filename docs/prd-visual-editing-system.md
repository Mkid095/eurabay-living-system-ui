# PRD: Visual Editing System

## Overview

The EURABAY Living System includes a sophisticated visual editing system that allows real-time UI modifications within an iframe environment. This system enables designers and developers to visually edit components, adjust styles, and preview changes instantly.

## Goals

- Enable real-time visual editing of UI components
- Provide element highlighting and selection
- Allow style injection and preview
- Support component tagging system
- Facilitate parent-child window communication
- Streamline UI customization workflow

## Current State

**Status:** ✅ FULLY IMPLEMENTED
- `VisualEditsMessenger.tsx` - Complete implementation
- `component-tagger-loader.js` - Webpack loader for component tagging
- All functionality is working

**Problem:** No documentation exists for this feature. It's implemented but not documented.

## User Stories

### US-001: Visual Editor Messenger System

**Description:** As a developer, I need a messenger system to handle visual editing communications.

**Acceptance Criteria:**
- [x] Create parent window message listener
- [x] Create iframe message sender
- [x] Handle element selection events
- [x] Handle style change events
- [x] Handle hover events
- [x] Handle click events
- [x] Support bidirectional communication
- [x] Typecheck passes
- [x] Verify cross-window messaging works

**Status:** ✅ COMPLETED

**Implementation:**
- Located in: `src/visual-edits/VisualEditsMessenger.tsx`
- Handles PostMessage API for cross-frame communication
- Supports event types: HOVER, CLICK, SELECT, STYLE_CHANGE

### US-002: Element Highlighting System

**Description:** As a designer, I need to visually highlight elements when editing.

**Acceptance Criteria:**
- [x] Highlight element on hover
- [x] Show element dimensions
- [x] Display element path/breadcrumb
- [x] Support multi-element selection
- [x] Remove highlight on deselect
- [x] Typecheck passes
- [x] Verify highlighting works in iframe

**Status:** ✅ COMPLETED

### US-003: Component Tagger System

**Description:** As a developer, I need to tag React components for identification.

**Acceptance Criteria:**
- [x] Create webpack loader for component tagging
- [x] Inject component names into DOM
- [x] Tag nested components correctly
- [x] Support functional components
- [x] Support class components
- [x] Typecheck passes
- [x] Verify component names appear in DOM

**Status:** ✅ COMPLETED

**Implementation:**
- Located in: `src/visual-edits/component-tagger-loader.js`
- Custom webpack loader that injects data-component attributes
- Automatically tags all React components

### US-004: Style Injection System

**Description:** As a designer, I need to inject and preview CSS changes instantly.

**Acceptance Criteria:**
- [x] Inject inline styles to elements
- [x] Preview style changes in real-time
- [x] Support Tailwind CSS classes
- [x] Support custom CSS properties
- [x] Revert styles on cancel
- [x] Typecheck passes
- [x] Verify style injection works

**Status:** ✅ COMPLETED

### US-005: Element Inspector

**Description:** As a designer, I need to inspect element properties.

**Acceptance Criteria:**
- [x] Display element tag name
- [x] Display component name
- [x] Display current styles
- [x] Display element dimensions
- [x] Display element position
- [x] Display CSS classes
- [x] Typecheck passes
- [x] Verify inspector shows correct data

**Status:** ✅ COMPLETED

## Functional Requirements

- FR-1: Visual editor must work in iframe environment
- FR-2: All style changes must be preview-able before saving
- FR-3: Component names must be automatically tagged
- FR-4: Element selection must be precise and reliable
- FR-5: Cross-window messaging must handle all event types
- FR-6: System must not interfere with production code

## Technical Considerations

### Dependencies
- PostMessage API for cross-frame communication
- Custom webpack loader for component tagging
- React refs for element access
- CSS-in-JS for style injection

### Security
- PostMessage origin validation required
- Only allow editing in development mode
- Sanitize all injected styles
- Disable in production builds

### Performance
- Minimal impact on bundle size
- Zero runtime overhead in production
- Efficient element selection algorithms
- Debounced style injection

## Implementation Status

✅ **FULLY IMPLEMENTED** - No additional work needed
- VisualEditsMessenger.tsx - Complete
- component-tagger-loader.js - Complete
- All user stories completed
- Ready for use

## Documentation Gap

This feature is **fully implemented** but was **not documented** in any previous PRD. This PRD fills that documentation gap.

## Success Metrics

- Visual editor activates in < 100ms
- Style previews render in < 50ms
- Element selection accuracy = 100%
- Zero production code interference

## Related Features

- Background animation system (uses similar techniques)
- Advanced scroll animations
- Error reporting system (uses same PostMessage approach)
