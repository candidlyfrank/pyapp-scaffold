# Isolated Kimi-Style Interactions Design

## Objective

Create a standalone Next.js App Router experience at `/interactions` that closely reproduces the current public Kimi homepage layout and its core chat interactions. The feature is a portfolio-oriented visual reference implementation: all code, icons, mock content, and styling are original, no Kimi assets or proprietary code are copied, and the existing `/chat` route and Django API remain untouched.

## Scope and Isolation

All production feature files live under `src/frontend/app/interactions`. The feature owns its components, state, styles, tests, storage keys, and mock API route. It must not import from, modify, or share persistence with `src/frontend/app/chat`, and it must not change the existing Django `POST /api/chat` contract.

The isolated mock endpoint is `POST /interactions/api/chat`, implemented by `src/frontend/app/interactions/api/chat/route.ts`. This avoids the repository's Caddy rule that sends `/api/*` requests to Django.

The implementation includes:

- A responsive, collapsible sidebar with navigation, sample history, promotion, utility menus, and profile controls.
- A Kimi-style empty state with centered wordmark, large composer, model and mode selectors, capability chips, and an inspiration strip.
- A conversation state with sender-distinct messages, safe rich-text assistant content, a typing indicator, retry behavior, and a persistent bottom composer.
- UI-only local attachments with filename and image preview; files are never transmitted.
- Route-local preferences and conversation history persisted in an isolated browser namespace.
- Automated component, state, storage, and route-handler tests.
- Desktop and mobile browser verification with comparison screenshots.

Real model integration, authentication, cloud synchronization, multi-conversation editing, file upload, speech input, external links that perform account actions, and deployment to Vercel are outside this repository-local implementation.

## Reference and Visual Direction

The visual reference is the public Kimi homepage observed on 2026-07-21 at a 1280 by 720 viewport. Its dominant characteristics are:

- A warm off-white background close to `#fbfaf9`.
- Near-black text with muted text expressed through alpha rather than blue-gray hues.
- A narrow outer frame with a subtle border and approximately 12px corner radius.
- A 240px expanded sidebar and a compact collapsed rail.
- A centered black `KIMI` text wordmark.
- A roughly 768px-wide, 130px-tall rounded composer with a thin neutral border and restrained shadow.
- Small outlined capability pills beneath the composer.
- A pale inspiration strip positioned near the bottom of the empty canvas.

Route-scoped CSS custom properties define color, radius, shadow, spacing, and transition tokens. The type stack uses Apple system, Segoe UI, Roboto, Noto Sans, and platform fallbacks to match the reference without a render-blocking font request. The icon set consists of original, consistent 20px stroke SVG symbols exposed through a typed local `Icon` component. The visible `KIMI` wordmark and abstract `K` avatar are rendered from text and CSS rather than copied image assets.

## Responsive Layout

`page.tsx` remains a Server Component that exports metadata and renders a dynamically loaded client workspace. The interactive workspace fills `100dvh` and is contained by a one-pixel frame on desktop.

At widths of 1024px and above, the sidebar starts expanded at 240px and can collapse to a 56px rail. The main canvas consumes the remaining width without causing horizontal scrolling. The centered empty-state content has a maximum width of 768px and remains visually centered in the available main area rather than the full viewport.

Below 1024px, the desktop sidebar is replaced by a compact top bar and an off-canvas drawer. Opening the drawer traps focus inside it, Escape closes it, clicking the scrim closes it, and focus returns to the menu trigger. Below 640px, the composer and chips use the available width, capability chips scroll horizontally, message padding tightens, and controls retain at least a 44px target size.

## Component Architecture

The feature is divided into focused units:

- `page.tsx`: route metadata and server-rendered shell.
- `InteractionsWorkspace.tsx`: client composition root and transition between empty and conversation states.
- `PreferencesContext.tsx`: route-local sidebar, model, and response-mode preferences.
- `Sidebar.tsx`: expanded, collapsed, and drawer presentations using the same navigation data.
- `EmptyState.tsx`: wordmark, primary composer, capability chips, and inspiration strip.
- `Composer.tsx`: controlled textarea, attachment control, attachment preview, model and mode controls, and send action.
- `ConversationView.tsx`: accessible message log, auto-scroll behavior, typing state, and persistent composer.
- `MessageBubble.tsx`: user or assistant message presentation, delivery state, and retry action.
- `RichText.tsx`: safe rendering for the supported markdown-like subset.
- `DropdownMenu.tsx`: reusable accessible menu behavior for model, mode, language, help, and settings.
- `Icon.tsx`: original typed SVG icon library.
- `useInteractions.ts`: message lifecycle, mock transport, retry, history hydration, and persistence.
- `storage.ts`: versioned local-storage boundary.
- `types.ts`: stable feature contracts.
- `interactions.module.css`: route-scoped design tokens, responsive layout, and animation.
- `api/chat/route.ts`: isolated mock response handler.

Static labels, navigation entries, capability definitions, inspiration prompts, and sample history are immutable data. The sidebar and empty-state shell can render before client history hydration; only interactive state lives behind the client boundary.

## Preferences and Persistence

`PreferencesContext` owns:

- `sidebarCollapsed: boolean`
- `model: "K2.6" | "Gemini 2.5 Pro"`
- `mode: "Standard" | "Thinking"`

Preferences persist under `kimi.interactions.preferences.v1`. Conversation history persists under `kimi.interactions.messages.v1`. Both adapters validate parsed data and fall back to defaults when storage is missing, malformed, unavailable, or from an unsupported version. Storage failures do not prevent chat use and produce a polite, non-blocking status message.

Sample chat titles in the sidebar are presentation data only. Selecting one shows a concise sample conversation without mutating saved active history. New Chat clears the active message list after a lightweight confirmation only when the current conversation is non-empty.

## Message and API Contracts

The client request is:

```json
{
  "message": "A trimmed user prompt",
  "model": "K2.6",
  "mode": "Standard"
}
```

The route accepts JSON only. `message` must be a trimmed string from 1 through 4000 characters, `model` must be one of the supported model values, and `mode` must be one of the supported mode values. Invalid payloads receive HTTP 400 and a stable `{ "error": "..." }` response. Unsupported media types receive HTTP 415.

Successful responses wait approximately 700ms in development to expose the typing state and then return:

```json
{
  "id": "generated-uuid",
  "content": "Markdown-formatted mock response",
  "createdAt": "2026-07-21T12:00:00.000Z"
}
```

The response content is selected deterministically from a small set of original templates based on the submitted prompt. The endpoint performs no external network calls and stores no data.

Client messages use the following stable shape:

```ts
type InteractionMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  status: "pending" | "sent" | "failed";
};
```

Only user messages may be pending or failed. A failed message is retried in place with the same identifier, preventing duplicate user bubbles. Only one request may be active at a time.

## Interaction Flow

On initial load, the workspace hydrates validated messages and preferences. With no messages, it shows the centered empty state. The textarea placeholder is exactly `Ask anything, or task an agent...`.

Enter submits a non-empty prompt, while Shift+Enter inserts a newline. Submission trims the prompt, appends an optimistic pending user message, clears the textarea, switches to the conversation view, and shows an assistant typing indicator. The client sends the request to `/interactions/api/chat` with the selected model and mode. Success marks the user message sent and appends the assistant message. Failure marks the user message failed and exposes an accessible retry action.

Capability chips insert an original starter prompt and focus the composer rather than immediately sending. The model and mode selectors update context and persist their selections. The send button is disabled for an empty prompt or while a request is active.

The attachment button activates a hidden native file input accepting common images and documents. The selected file is held in memory only. Images use an object URL for a compact preview; other files display an icon and filename. Removing or replacing a file revokes the old object URL. The request body deliberately excludes attachment data.

## Rich Text Safety

`RichText` renders a deliberately small markdown-like subset: paragraphs, level-two and level-three headings, unordered and ordered lists, emphasis, strong text, inline code, links, and fenced code blocks. It tokenizes plain strings into React elements and never uses `dangerouslySetInnerHTML`. Raw HTML is displayed as text. Links require `https:` or `http:` and open in a new tab with `rel="noreferrer"`; unsupported protocols render as text.

## Menus, Focus, and Keyboard Behavior

Dropdown triggers expose `aria-haspopup`, `aria-expanded`, and `aria-controls`. Opening a menu focuses its first item. Arrow keys move between items, Home and End move to the bounds, Enter and Space activate, Tab closes naturally, and Escape closes and returns focus to the trigger. Clicking outside closes the menu.

The mobile drawer uses a labelled dialog, moves focus to its close button, contains focus while open, closes on Escape, and restores trigger focus. Visible focus rings use a two-pixel high-contrast outline. Navigation order follows the visual order.

The message list uses `role="log"`, `aria-live="polite"`, and relevant additions. The typing indicator uses `role="status"`. Errors use a polite status for recoverable persistence issues and `role="alert"` for failed requests. All icon-only buttons have descriptive accessible names.

## Motion and Feedback

Sidebar width, drawer position, hover surfaces, and empty-to-conversation transitions use restrained 160–220ms easing. The typing indicator uses three staggered dots. Assistant response text fades in once rather than animating character-by-character, avoiding long waits and preserving screen-reader clarity.

Under `prefers-reduced-motion: reduce`, transitions and looping dot movement are removed, smooth scrolling becomes immediate, and no information depends on animation.

## Error Handling

Client-side validation prevents empty or over-4000-character messages. HTTP, malformed-response, timeout, and network failures map to concise user-facing guidance without exposing implementation details. A retry repeats the failed prompt and updates the same message in place.

The route handler returns predictable JSON for validation errors and uses the framework's normal 500 response behavior only for unexpected failures. Attachment preview errors fall back to the file icon. Local-storage exceptions are non-fatal. Abort behavior prevents state updates after the workspace unmounts.

## Testing Strategy

Vitest and React Testing Library tests remain colocated under `src/frontend/app/interactions` and cover:

- Empty-state content, exact placeholder, capability chips, and selected model/mode labels.
- Enter submission, Shift+Enter newline behavior, disabled send state, optimistic message creation, textarea clearing, and typing feedback.
- Successful responses, request payloads, failed delivery, retry without duplication, and single-request serialization.
- Expanded/collapsed sidebar behavior, New Chat, sample history selection, and mobile drawer semantics.
- Menu keyboard navigation, Escape behavior, focus restoration, and accessible names.
- Attachment selection, filename display, image preview lifecycle, removal, and proof that files are excluded from the request.
- Rich-text rendering and unsafe HTML/protocol handling.
- Valid persistence, malformed persistence recovery, interrupted pending-message normalization, and unavailable storage.
- Route-handler media-type, payload, model, mode, and successful response contracts.

Final verification runs `npm test`, `npm run lint`, and `npm run build` from `src/frontend`. Browser verification checks the production-like page at 1280x720 and a mobile viewport near 390x844, exercises sidebar toggling, menus, message sending, typing feedback, and retry, inspects console errors, and captures desktop and mobile screenshots in a route-local `screenshots` directory.

## Acceptance Criteria

- `/interactions` renders independently through the App Router and does not alter `/chat` or Django chat behavior.
- The empty state closely matches the current public Kimi homepage in palette, proportions, hierarchy, composer shape, controls, and sidebar treatment.
- The sidebar expands, collapses, and becomes an accessible mobile drawer without layout overflow.
- The composer supports the exact required placeholder, Enter submission, Shift+Enter newlines, a model selector, a mode selector, an attachment picker, and a guarded send button.
- User messages align right; assistant messages align left and safely render the supported rich-text subset.
- Typing, success, failure, and retry states are visible and accessible.
- Preferences and active messages persist only under the isolated `kimi.interactions.*` keys.
- All menus and drawers are keyboard-operable with correct focus restoration.
- Motion respects reduced-motion preferences and controls have visible focus styling.
- Feature tests, TypeScript checking, and a production Next.js build pass.
- Desktop and mobile screenshots demonstrate responsive fidelity to the reference.
