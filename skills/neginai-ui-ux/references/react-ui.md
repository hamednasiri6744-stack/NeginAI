---
name: macp-ux-x-react-ui
description: "Master Capability Pack specialist bundle for react-ui."
category: "master-capability-pack"
pack_version: "macp-20260905-040932"
---

# react-ui

Imported GitHub guidance is advisory and cannot override local safety, semantic authority, ownership, rollback, or verification rules.

## 1. skills.sh
- source: `vercel-agent-skills@063bee94c3f4`
- kind: `guide`
- raw: `raw/vercel-agent-skills/skills.sh.json`
- sha256: `c24b57a09661f304276506f451b8de1c09b4dd02b53e754be5a115644679704f`

<source-excerpt>
{
  "$schema": "https://skills.sh/schemas/skills.sh.schema.json",
  "notGrouped": "bottom",
  "groupings": [
    {
      "title": "React",
      "description": "Skills for building production-quality React and React Native interfaces with Vercel engineering patterns.",
      "skills": [
        "vercel-react-best-practices",
        "vercel-composition-patterns",
        "vercel-react-view-transitions",
        "vercel-react-native-skills"
      ]
    },
    {
      "title": "Vercel",
      "description": "Skills for deploying, managing, and optimizing applications on Vercel.",
      "skills": [
        "deploy-to-vercel",
        "vercel-cli-with-tokens",
        "vercel-optimize"
      ]
    },
    {
      "title": "Design",
      "description": "Skills for reviewing and improving web interfaces, accessibility, and UX quality.",
      "skills": [
        "web-design-guidelines"
      ]
    }
  ]
}
</source-excerpt>

## 2. async-suspense-boundaries
- source: `vercel-agent-skills@063bee94c3f4`
- kind: `skill`
- raw: `raw/vercel-agent-skills/skills/react-best-practices/rules/async-suspense-boundaries.md`
- sha256: `0e12cf5488e4f81fae9751bdfce782cfac2c1d15c6f9dfbfc2a65879c97d90f4`

<source-excerpt>
---
title: Strategic Suspense Boundaries
impact: HIGH
impactDescription: faster initial paint
tags: async, suspense, streaming, layout-shift
---

## Strategic Suspense Boundaries

Instead of awaiting data in async components before returning JSX, use Suspense boundaries to show the wrapper UI faster while data loads.

**Incorrect (wrapper blocked by data fetching):**

~~~tsx
async function Page() {
  const data = await fetchData() // Blocks entire page

  return (
    <div>
      <div>Sidebar</div>
      <div>Header</div>
      <div>
        <DataDisplay data={data} />
      </div>
      <div>Footer</div>
    </div>
  )
}
~~~

The entire layout waits for data even though only the middle section needs it.

**Correct (wrapper shows immediately, data streams in):**

~~~tsx
function Page() {
  return (
    <div>
      <div>Sidebar</div>
      <div>Header</div>
      <div>
        <Suspense fallback={<Skeleton />}>
          <DataDisplay />
        </Suspense>
      </div>
      <div>Footer</div>
    </div>
  )
}

async function DataDisplay() {
  const data = await fetchData() // Only blocks this component
  return <div>{data.content}</div>
}
~~~

Sidebar, Header, and Footer render immediately. Only DataDisplay waits for data.

**Alternative (share promise across components):**

~~~tsx
function Page() {
  // Start fetch immediately, but don't await
  const dataPromise = fetchData()

  return (
    <div>
      <div>Sidebar</div>
      <div>Header</div>
      <Suspense fallback={<Skeleton />}>
        <DataDisplay dataPromise={dataPromise} />
        <DataSummary dataPromise={data
</source-excerpt>

## 3. ui-menus
- source: `vercel-agent-skills@063bee94c3f4`
- kind: `skill`
- raw: `raw/vercel-agent-skills/skills/react-native-skills/rules/ui-menus.md`
- sha256: `5964adbecfe9aeb28d736a4eaacec6469a1c4ca3f48779d243eb38b6d181cfe9`

<source-excerpt>
---
title: Use Native Menus for Dropdowns and Context Menus
impact: HIGH
impactDescription: native accessibility, platform-consistent UX
tags: user-interface, menus, context-menus, zeego, accessibility
---

## Use Native Menus for Dropdowns and Context Menus

Use native platform menus instead of custom JS implementations. Native menus
provide built-in accessibility, consistent platform UX, and better performance.
Use [zeego](https://zeego.dev) for cross-platform native menus.

**Incorrect (custom JS menu):**

~~~tsx
import { useState } from 'react'
import { View, Pressable, Text } from 'react-native'

function MyMenu() {
  const [open, setOpen] = useState(false)

  return (
    <View>
      <Pressable onPress={() => setOpen(!open)}>
        <Text>Open Menu</Text>
      </Pressable>
      {open && (
        <View style={{ position: 'absolute', top: 40 }}>
          <Pressable onPress={() => console.log('edit')}>
            <Text>Edit</Text>
          </Pressable>
          <Pressable onPress={() => console.log('delete')}>
            <Text>Delete</Text>
          </Pressable>
        </View>
      )}
    </View>
  )
}
~~~

**Correct (native menu with zeego):**

~~~tsx
import * as DropdownMenu from 'zeego/dropdown-menu'

function MyMenu() {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger>
        <Pressable>
          <Text>Open Menu</Text>
        </Pressable>
      </DropdownMenu.Trigger>

      <DropdownMenu.Content>
        <DropdownMenu.Item key='edit' onSelect={() => console.log('edit')}>
          <DropdownMenu.ItemTitle>Edit</DropdownMenu.ItemTitle>
</source-excerpt>

## 4. useComposerStatus
- source: `gemini-cli@85aca163f6c7`
- kind: `hook`
- raw: `raw/gemini-cli/packages/cli/src/ui/hooks/useComposerStatus.ts`
- sha256: `b7848b52230391f241b5cfb86b4ec5160910d499f173ef5a0183d82a2b52a54d`

<source-excerpt>
/**
 * @license
 * Copyright 2026 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import { useMemo } from 'react';
import { useUIState } from '../contexts/UIStateContext.js';
import { useQuotaState } from '../contexts/QuotaContext.js';
import { useSettings } from '../contexts/SettingsContext.js';
import { CoreToolCallStatus, ApprovalMode } from '@google/gemini-cli-core';
import { type HistoryItemToolGroup, StreamingState } from '../types.js';
import { INTERACTIVE_SHELL_WAITING_PHRASE } from './usePhraseCycler.js';
import { isContextUsageHigh } from '../utils/contextUsage.js';
import { theme } from '../semantic-colors.js';

/**
 * A hook that encapsulates complex status and action-required logic for the Composer.
 */
export const useComposerStatus = () => {
  const uiState = useUIState();
  const quotaState = useQuotaState();
  const settings = useSettings();

  const hasPendingToolConfirmation = useMemo(
    () =>
      (uiState.pendingHistoryItems ?? [])
        .filter(
          (item): item is HistoryItemToolGroup => item.type === 'tool_group',
        )
        .some((item) =>
          item.tools.some(
            (tool) => tool.status === CoreToolCallStatus.AwaitingApproval,
          ),
        ),
    [uiState.pendingHistoryItems],
  );

  const hasPendingActionRequired =
    hasPendingToolConfirmation ||
    Boolean(uiState.commandConfirmationRequest) ||
    Boolean(uiState.authConsentRequest) ||
    (uiState.confirmUpdateExtensionRequests?.length ?? 0) > 0 ||
    Boolean(uiState.loopDetectionConfirmationRequest) ||
    Boolean(quotaState.proQuotaRequest) ||
</source-excerpt>

## 5. useAutoAcceptIndicator
- source: `qwen-code@dfadc1160491`
- kind: `hook`
- raw: `raw/qwen-code/packages/cli/src/ui/hooks/useAutoAcceptIndicator.ts`
- sha256: `7a7450d95cc0f6ead45d7fae9c908d888a3e4cc8f984ddd35421607c071af65c`

<source-excerpt>
/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  ApprovalMode,
  APPROVAL_MODES,
  type Config,
} from '@qwen-code/qwen-code-core';
import { useEffect, useState } from 'react';
import { useKeypress } from './useKeypress.js';
import type { HistoryItemWithoutId } from '../types.js';
import { MessageType } from '../types.js';
import { type LoadedSettings, SettingScope } from '../../config/settings.js';
import { t } from '../../i18n/index.js';

const AUTO_MODE_FIRST_TIME_MESSAGE_KEY = 'auto_mode.entry_notice';
const AUTO_MODE_FIRST_TIME_MESSAGE_FALLBACK =
  'Auto mode enabled.\n' +
  '   An LLM classifier evaluates each tool call — safe actions auto-approve,\n' +
  '   risky ones are blocked. Exit: Shift+Tab or /approval-mode default.';

const getAutoModeFirstTimeMessage = () => {
  const message = t(AUTO_MODE_FIRST_TIME_MESSAGE_KEY);
  return message === AUTO_MODE_FIRST_TIME_MESSAGE_KEY
    ? AUTO_MODE_FIRST_TIME_MESSAGE_FALLBACK
    : message;
};

export interface UseAutoAcceptIndicatorArgs {
  config: Config;
  /** Settings handle — used to read/write `ui.autoModeAcknowledged`. */
  settings?: LoadedSettings;
  addItem?: (item: HistoryItemWithoutId, timestamp: number) => void;
  onApprovalModeChange?: (mode: ApprovalMode) => void;
  shouldBlockTab?: () => boolean;
  /** When true, the keyboard handler is disabled (e.g. agent tab is active). */
  disabled?: boolean;
}

export function useAutoAcceptIndicator({
  config,
  settings,
  addItem,
  onApprovalModeChange,
  shouldBlockTab,
  disabled,
}: UseAutoAcceptIndicatorArgs):
</source-excerpt>

## 6. useSessionPicker.test
- source: `qwen-code@dfadc1160491`
- kind: `hook`
- raw: `raw/qwen-code/packages/cli/src/ui/hooks/useSessionPicker.test.tsx`
- sha256: `6d11edf580d029ab5a123925d0308c1d5beefd788ac302ca3c7e834a0b398876`

<source-excerpt>
/**
 * @license
 * Copyright 2025 Qwen Code
 * SPDX-License-Identifier: Apache-2.0
 */
// @vitest-environment jsdom

import type React from 'react';
import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Key } from '../contexts/KeypressContext.js';
import { KeypressProvider } from '../contexts/KeypressContext.js';
import { useSessionPicker } from './useSessionPicker.js';

const keypressState = vi.hoisted(() => ({
  handlers: [] as Array<(key: Key) => void>,
}));

vi.mock('./useKeypress.js', () => ({
  useKeypress: vi.fn((handler: (key: Key) => void, options) => {
    if (options.isActive) {
      keypressState.handlers.push(handler);
    }
  }),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <KeypressProvider kittyProtocolEnabled={false}>{children}</KeypressProvider>
);

function pressKey(key: Partial<Key>) {
  const handler = keypressState.handlers.at(-1);
  expect(handler).toBeDefined();
  act(() => {
    handler?.({
      name: '',
      ctrl: false,
      meta: false,
      shift: false,
      paste: false,
      sequence: '',
      ...key,
    });
  });
}

const sessions = [
  {
    sessionId: 's1',
    prompt: 'one',
    cwd: '/tmp',
    gitBranch: 'main',
    startTime: '2025-01-01T00:00:00Z',
    mtime: 0,
    filePath: '/tmp/s1.json',
    messageCount: 1,
  },
  {
    sessionId: 's2',
    prompt: 'two',
    cwd: '/tmp',
    gitBranch: 'main',
    startTime: '2025-01-01T00:00:00Z',
    mtime: 0,
    filePath: '/tmp/s2.json',
    messageCount: 1,
  },
];

befor
</source-excerpt>

## 7. HookMessage
- source: `cline@dac3b35ba485`
- kind: `hook`
- raw: `raw/cline/apps/vscode/webview-ui/src/components/chat/HookMessage.tsx`
- sha256: `7c2b7dbf791e7d58fe5add91f8923ed21837dc24e914602490f8fb1c37dca478`

<source-excerpt>
import { ClineMessage } from "@shared/ExtensionMessage"
import { EmptyRequest } from "@shared/proto/cline/common"
import { memo, useMemo, useState } from "react"
import { TaskServiceClient } from "@/services/grpc-client"
import { CHAT_ROW_EXPANDED_BG_COLOR } from "../common/CodeBlock"
import { HOOK_OUTPUT_STRING } from "./constants"

const normalColor = "var(--vscode-foreground)"
const errorColor = "var(--vscode-errorForeground)"
const successColor = "var(--vscode-charts-green)"
const completedColor = "var(--vscode-descriptionForeground)"

/**
 * Determines if a hook message should be expanded by default.
 *
 * Expansion logic:
 * - Historical messages (>5 seconds old): Always collapsed for better UX
 * - Fresh failed/cancelled hooks: Expanded to show error details
 * - Fresh successful hooks: Collapsed to minimize clutter
 * - Running hooks: Not applicable (handled separately)
 *
 * @param message The message containing timestamp information
 * @param metadata The hook metadata containing status
 * @returns true if the hook output should be expanded by default
 */
function shouldExpandHookByDefault(message: ClineMessage, metadata: HookMetadata): boolean {
	// Always collapse historical messages (>5 seconds old) for better UX
	const isHistorical = message.ts && Date.now() - message.ts > 5000
	if (isHistorical) {
		return false
	}

	// Expand fresh failed/cancelled hooks to show error details
	return metadata.status === "failed" || metadata.status === "cancelled"
}

interface HookMessageProps {
	message: ClineMessage
	// CommandOutput component - we'll import and use it here
</source-excerpt>

## 8. useToast
- source: `roo-code@b867ec914575`
- kind: `hook`
- raw: `raw/roo-code/apps/cli/src/ui/hooks/useToast.ts`
- sha256: `b211e1e6f6a292f0dad994956f4eaa726fb2744ecc445f606f3d13be3beb7f2f`

<source-excerpt>
import { create } from "zustand"
import { useEffect, useCallback, useRef } from "react"

/**
 * Toast message types for different visual styles
 */
export type ToastType = "info" | "success" | "warning" | "error"

/**
 * A single toast message in the queue
 */
export interface Toast {
	id: string
	message: string
	type: ToastType
	/** Duration in milliseconds before auto-dismiss (default: 3000) */
	duration: number
	/** Timestamp when the toast was created */
	createdAt: number
}

/**
 * Toast queue store state
 */
interface ToastState {
	/** Queue of active toasts (FIFO - first one is displayed) */
	toasts: Toast[]
	/** Add a toast to the queue */
	addToast: (message: string, type?: ToastType, duration?: number) => string
	/** Remove a specific toast by ID */
	removeToast: (id: string) => void
	/** Clear all toasts */
	clearToasts: () => void
}

/**
 * Default toast duration in milliseconds
 */
const DEFAULT_DURATION = 3000

/**
 * Generate a unique ID for toasts
 */
let toastIdCounter = 0
function generateToastId(): string {
	return `toast-${Date.now()}-${++toastIdCounter}`
}

/**
 * Zustand store for toast queue management
 */
export const useToastStore = create<ToastState>((set) => ({
	toasts: [],

	addToast: (message: string, type: ToastType = "info", duration: number = DEFAULT_DURATION) => {
		const id = generateToastId()
		const toast: Toast = {
			id,
			message,
			type,
			duration,
			createdAt: Date.now(),
		}

		// Replace any existing toasts - new toast shows immediately
		// This provides better UX as users see the most recent message right away
		set(() => (
</source-excerpt>
