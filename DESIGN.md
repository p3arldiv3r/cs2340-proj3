# DESIGN.md — Social Wellness Platform for Older Adults

Working name: **[Name]** (placeholder from the wireflows).
Chosen visual direction: **Garden** (calm, natural, soft shapes).
Scope: responsive web + mobile web/app, one shared design system.
Source material: Story 13 (recommended programs and calendar reminders) and Story 14 (personalized recommendations) wireflows, plus the Garden mockups in the design directions canvas.

---

## 1. Product principles

1. **Company first, technology second.** Every screen should make the next human connection feel closer, not make the user manage software.
2. **The user is always in control.** Nothing is saved, shared, created, or sent without a visible, plain-language confirmation. (Already modeled in Story 13 step 03.)
3. **Show your work.** Every recommendation has a checkable source ("View source 1") and an explanation of how preferences were used. Trust is the core feature of the RAG assistant.
4. **A reminder is not a registration.** Calendar, saved lists, and sign-ups are separate concepts and the UI never blurs them.
5. **Calm over clever.** No timers, no streak pressure, no guilt copy, no auto-playing motion. Older adults should never feel behind.
6. **One clear thing first.** Each screen has one obvious primary item and one primary action. Everything else is visibly quieter (see 4.3).
7. **Design for the hardest case, benefit everyone.** Low vision, tremor, reduced dexterity, hearing loss, cognitive load, low digital confidence, and screen-reader use are baseline conditions, not edge cases.

---

## 2. Accessibility standard

Target: **WCAG 2.2 AA minimum, AAA where practical** (contrast, target size, reading level). Test with VoiceOver (iOS/macOS), TalkBack (Android), NVDA/JAWS, keyboard only, 200% and 400% zoom, and OS "Larger Text" at maximum.

### 2.1 Vision
- **Body text 18px minimum (web) / 18pt equivalent with Dynamic Type and Android font scaling honored up to 200%.** Default body: 21px on web, 19px on mobile.
- Body text contrast **7:1 (AAA)**; large text and UI components **4.5:1 minimum**. Never rely on color alone (always pair with icon + text).
- Line height 1.45–1.6, line length 45–70 characters, left-aligned, never justified.
- No text in images. Every informative image has meaningful alt text; decorative images (including the leaf motif) use `alt=""` or `aria-hidden="true"`.
- Layout must reflow at 400% zoom with no horizontal scroll (WCAG 1.4.10).
- Provide a visible **Text size** control (A / A+ / A++) and a **High contrast** toggle in the header or account menu, persisted per account.
- Support light, dark, and OS high-contrast / forced-colors modes. Default is light. Dark mode keeps the green/sage character (see 3.1 note).
- **Decorative low-contrast elements** (soft card outlines, sage panels, the leaf motif) are never the only thing that marks a control or conveys meaning.

### 2.2 Motor and touch
- **Touch/click targets: 48×48px minimum, 56px for primary actions**, with 12px minimum spacing between adjacent targets.
- No drag-only, hover-only, long-press-only, or multi-finger gestures. Every gesture has a single-tap equivalent.
- Forgiving interaction: destructive or hard-to-undo actions need a confirm step; most actions offer **Undo** for 10+ seconds.
- No time limits on forms or chat. Session timeouts warn at least 2 minutes before and can be extended with one tap.
- Voice input available in chat and journal fields (platform dictation supported and not blocked).

### 2.3 Hearing
- All audio/video has captions and transcripts. Notifications never rely on sound alone (use text + vibration + visual).
- Online group join links display whether the session is video, audio-only, or phone dial-in, with captioning availability noted by the provider.

### 2.4 Cognitive and language
- **Plain language, target reading level grade 6–8.** Short sentences. Active voice. No jargon ("RAG", "retrieval", "token", "sync").
- One primary action per screen. Progressive disclosure for secondary options.
- Consistent navigation labels and positions across pages. Labels are words, not icons alone. Do not abbreviate labels to fit (use "Assistant", not "Assist").
- Always show where you are (page heading + current nav state) and how to go back.
- Error messages say what happened and what to do next, never blame the user.
- Chat assistant uses short replies, offers 2–4 tappable quick replies, and never makes the user retype what it already knows.
- Multilingual-ready layout (text expands up to 40%); content structured for translation. Priority languages to be decided by the team.

### 2.5 Screen readers and keyboard
- Semantic HTML first (`header`, `nav`, `main`, `section`, `button`, `a`), ARIA only to fill gaps.
- One `h1` per page; headings never skipped. Landmarks labeled ("Main navigation", "Assistant conversation").
- Visible focus indicator: 3px solid outline in `focus.ring`, 3px offset so it sits on the page background (not against the button fill), never removed. Ring contrast is 7.6:1 on `bg.page` and 8.3:1 on `bg.surface`.
- Skip link ("Skip to main content") is the first focusable element.
- Logical tab order equals visual order. Modals/sheets trap focus, close on Esc, and return focus to the trigger.
- **Chat:** conversation is a labeled `log` region (`role="log"`, `aria-live="polite"`). Assistant replies announce once, complete, not token by token. Streaming is visual only; announce on completion. A "Stop" button is always reachable.
- **Status messages** (saved, created, error) use `role="status"` / `role="alert"` appropriately and also appear as visible text on the page.
- Source citations are real links with descriptive text: "View source 1: Curated group directory, Afternoon Book Circle", not just "View source 1" alone (the visible label can stay short; add the full name via `aria-label`).
- Dates and times are written out ("Thursday, November 5, 2026, 3:00 to 4:00 PM Eastern Time"), with a machine-readable `<time>` element.
- Checkbox and radio groups use `fieldset`/`legend`. Selected state is exposed programmatically (not only a check icon).

### 2.6 Motion
- Respect `prefers-reduced-motion`. Default motion is minimal: 150–200ms fades only. No parallax, no auto-carousels, no auto-playing media. The leaf motif is static.

### 2.7 Accessibility acceptance checklist (per screen)
- [ ] Works with keyboard only
- [ ] Works at 200% text size and 400% zoom
- [ ] All text/UI contrast verified
- [ ] Screen reader pass: heading order, landmarks, names/roles/states
- [ ] Targets ≥ 48px with spacing
- [ ] No info conveyed by color alone
- [ ] Plain-language copy reviewed
- [ ] Tested with at least 3 older adult participants before release

---

## 3. Design tokens — "Garden"

### 3.1 Color

| Token | Hex | Use | Contrast |
|---|---|---|---|
| `bg.page` | `#F3F6EE` | Page background (pale sage) | — |
| `bg.surface` | `#FFFFFF` | Cards, inputs, header, nav | — |
| `bg.sage` | `#E4EDDC` | Info panels, selected rows, "how I chose these" strip | — |
| `bg.plum` | `#F1E6EE` | Resource cards, gentle highlights | — |
| `text.primary` | `#1D2B20` | Body, headings | 13.6:1 on `bg.page`, 14.8:1 on surface, 12.3:1 on sage |
| `text.secondary` | `#3F4F43` | Supporting text | 8.0:1 on `bg.page`, 7.2:1 on sage |
| `brand.primary` | `#2F5D3A` | Primary buttons, links, active nav, logo | 7.6:1 white on it; 7.0:1 on `bg.page` |
| `brand.primary-hover` | `#244A2E` | Hover/pressed | — |
| `accent.plum` | `#7A3E65` | Type tags, small highlights | 7.1:1 on `bg.page`, 7.8:1 on surface |
| `text.on-plum` | `#3A1D31` | Text on `bg.plum` | 12.4:1 |
| `border.strong` | `#5E6F61` | Input borders, secondary button outlines, chips | 4.9:1 on `bg.page` (passes 3:1) |
| `border.soft` | `#C9D5C4` | Decorative card outlines, dividers only | 1.4:1, **decorative only** |
| `status.success` | `#1E6B3A` | Confirmed, created | 6.5:1 on surface; with ✓ icon + text |
| `status.warning` | `#8A5A00` | Needs attention | 5.9:1 on surface; with ⚠ icon + text |
| `status.error` | `#A12622` | Errors | 7.5:1 on surface; with ✕ icon + text |
| `status.info` | `#1F4E8C` | Notes | 8.3:1 on surface; with ℹ icon + text |
| `focus.ring` | `#1F4E8C` | Focus outline | 7.6:1 on `bg.page`, 8.3:1 on surface |

Rules:
- Success green (`status.success`) and brand green are close in hue. Success always includes a ✓ icon and the word ("Created", "Saved") so it is never confused with a plain brand element.
- Plum is an accent, not a second brand color. Use it for type tags and the resource card only.
- Interactive controls always use `brand.primary` or `border.strong`; never `border.soft`.
- **Dark mode (to design):** page `#14201A`, surface `#1C2B22`, text `#EAF1E6`, primary `#8FCB9B`, plum `#E3B5D3`. Re-verify every pair before launch.
- All values to be re-verified with a contrast tool before launch.

### 3.2 Typography
- **Headings:** Fraunces (variable serif), weight 500–600. Warm and soft without being childish. Fallback: Georgia, serif.
- **Body/UI:** Nunito Sans, 400/600/700. Rounded terminals match the pill shapes. Fallback: system-ui, sans-serif.
- If the team prefers maximum legibility for low vision, swap the body face to Atkinson Hyperlegible without changing anything else.
- Never use weights under 400 or all-caps for body copy. Small caps labels (type tags, section labels) are 16px, 700, letter-spaced, and always accompany text that says the same thing in words.

| Style | Web | Mobile | Face / weight |
|---|---|---|---|
| Display | 44/52 | 34/42 | Fraunces 600 |
| H1 | 42/50 | 32/40 | Fraunces 600 |
| H2 | 34/42 (hero card title) | 28/34 | Fraunces 600 |
| H3 | 26/32 | 24/30 | Fraunces 600 |
| Body | 21/31 | 19/28 | Nunito Sans 400 |
| Body small | 18/27 | 18/26 | Nunito Sans 400 (dates, metadata) |
| Label/Button | 20/24 | 19/24 | Nunito Sans 700 |
| Tag / section label | 16/20 | 16/20 | Nunito Sans 700, uppercase, +0.06em |

Minimum text size anywhere in the product: 16px, only for tags and non-essential metadata.

### 3.3 Spacing, shape, elevation
- Spacing scale (px): 4, 8, 12, 16, 24, 32, 48, 64. Hero card padding 32 (web) / 22 (mobile). Secondary card padding 20–24.
- **Radius:** buttons, nav items, chips and tags are fully rounded (pill, 999px). Cards 24px, hero card 28px, input fields 14px.
- Elevation: none by default. Cards are separated by outline (`border.strong` for the primary card, `border.soft` for secondary) and fill, not shadow.
- **Leaf motif:** one soft leaf shape (sage fill, green stem line) may sit in the top-right corner of the hero recommendation card. Decorative only, `aria-hidden`, never behind text, never animated. Use it on one card per screen at most.

### 3.4 Breakpoints
- Mobile: 360–599px (single column, floating bottom nav)
- Tablet: 600–1023px (single column wide, side-by-side where it helps)
- Desktop: 1024px+ (max content width 1120px; reading column 720–760px)

---

## 4. Navigation and layout

Primary destinations: **Home, My groups, Assistant, Journal, Help**, plus the account menu. Calendar lives under My groups.

### 4.1 Navigation
- **Web:** top bar on a white surface. Nav items are pills; the current page is a filled `brand.primary` pill with white text, plus `aria-current="page"`. Text size control (A / A+ / A++) and "Your account" sit at the right.
- **Mobile:** **floating pill bar** at the bottom with 5 tabs, each icon + visible full text label, 64px tall. Current tab is a filled green pill. Header holds the logo and a "Text size" button.
- **Help is always visible and always one tap away**, with an "Ask a person" option, not only the chatbot.
- Persistent footer line on web and in the Help tab on mobile: **"Need to talk to someone now? Call or text 988, any time."** (US; localize for other regions).
- Every sub-screen has an explicit "Back to ..." button.

### 4.2 Page structure
Every page follows the same top-to-bottom order:
1. Page heading (H1) and one plain sentence of context.
2. The primary item (hero card) with one primary action.
3. Secondary items, visibly quieter.
4. Controls that change what you see ("Refine my suggestions", "How I chose these").
5. Safety and help line.

### 4.3 Visual hierarchy rules
- **One hero per screen.** Hero card: white, 2px `brand.primary` outline, largest title, solid green primary button.
- **Secondary cards:** smaller title, `border.soft` outline, text-style link actions only (no filled buttons).
- **Resource card:** `bg.plum`, no outline, no buttons, clearly different from recommendations.
- **Context strip** ("How I chose these") is a single sage band below the content, with chips and the two utility buttons. It never sits beside the content competing with the hero.
- If more than 3 secondary items exist, show 3 and add a "See all" link.

### 4.4 Desktop layout
- Hero card spans roughly 58% of the width; secondary cards stack in a column beside it (as in the Garden mockup). Below: the sage context strip, then the footer help line.
- Above 1280px, content stays centered in a 1120px container.

### 4.5 Mobile layout
- Single column in this order: heading, hero card (full-width buttons stacked), secondary card(s), then the context strip as a collapsible "How I chose these" section.
- Buttons are full width, 56px tall, stacked with 10px gaps.

---

## 5. Core components

### 5.1 Buttons
- **Primary:** filled `brand.primary`, white text, pill, min height 56px.
- **Secondary:** white fill, 2px `brand.primary` outline and text, pill, 56px (48px in dense areas).
- **Tertiary:** text only, underlined, `text.primary`, 48px tall hit area.
- Label is a verb phrase: "Add to my list", "Find something for me", "Confirm & create 2 events".
- Disabled buttons are avoided; show the reason instead ("Choose at least one session to continue").

### 5.2 Assistant chat
- Header: "Your assistant" with a short line: "I can help you find groups, plan your day, and answer questions. I'm not a person, and I can't give medical advice."
- Bubbles: assistant on `bg.sage`, user on white with `border.strong`, both with text labels ("Assistant", "You") so alignment and color are not the only distinction. Bubble radius 24px.
- Quick-reply chips (pills, min 48px) under each assistant question.
- Input: large text field, Send button with text label, microphone button for dictation.
- Sources: citation links with descriptive text; expandable "How I chose this" section.
- Privacy toggle visible next to the input: **"Use my previous conversations for suggestions"** (checked state clearly shown).
- Always show a "Talk to a person" option within the chat.

### 5.3 Recommendation card
Order of fields: **Type tag** (plum, "Group · Online · Afternoon") → **Title** (Fraunces) → **One-line description** → **When / cost / where** (bold) → **Why this fits** → **Actions**.
- *Hero version:* all fields, actions = "Add to my list" (primary), "View source 1" (secondary), "Not for me" (tertiary).
- *Secondary version:* tag, title, when/cost, "View source N" as a text link. Short description and "Why this fits" are shown after tapping into the card.
- "Why this fits" is mandatory on the hero card and in plain language ("You enjoy books. You're looking for online afternoon activities.").
- In-person results also show distance, accessibility info (step-free entrance, seating, restrooms), and transport notes.
- "Not for me" removes the card, shows an Undo for 10 seconds, and feeds back into suggestions.

### 5.4 Source panel (Story 14, step 04)
- Quoted record text, record ID, provider, plus **"How your preferences were used"** (which preference came from an earlier chat vs. today's message).
- Prominent "Back to suggestions" button. Focus returns to the originating card.
- Includes "Report a problem with this suggestion".

### 5.5 Context strip: "How I chose these"
- Sage band (`bg.sage`, radius 24px) with chips: "Books · earlier chat", "Online · today", "Afternoon · today". Each chip is removable (a Remove control with a 48px target; the chip text says where it came from).
- On the right (web) or below (mobile): "Refine my suggestions" (primary) and "Talk to a person" (secondary).
- One-line reminder: "You choose what to share. Suggestions come from our curated group directory."

### 5.6 Program list with selection (Story 13, step 02)
- Checkbox rows with 48px+ hit areas covering the whole row. Selected state = checkmark + `border.strong` → 3px `brand.primary` border + `bg.sage` fill + "Selected" text for screen readers and sighted users.
- Sticky summary bar: "2 of 3 selected · No events created yet" with the action "Review 2 events".
- Persistent helper text: "Calendar reminders are not program registration."

### 5.7 Review-and-confirm panel (Story 13, step 03)
- Shows every field that will be created: title, date/time, time zone, join link, one-time vs repeating, calendar target, reminder choices.
- Explicit consent checkbox: "I confirm these details and allow Assistant to create these 2 events in My calendar."
- Primary action label includes the count. A visible "Back to program list" is always available.
- Time zone is shown with a "Change" control; default from account, not guessed silently.

### 5.8 Success/confirmation (Story 13, step 04)
- Top of page: status line with ✓ icon in `status.success`. Summary of what was created **and what was not** ("Poetry Together was not selected and has not been added to your calendar").
- Standing notice: "A reminder is not a registration." Include sign-up requirements per program.
- Next steps: "Open My calendar", "Back to saved program list".

### 5.9 Interest tags
- Interactive tags are real buttons (toggle with `aria-pressed`), pill shape, min 48px tall. Selected = `bg.sage` fill + `brand.primary` 3px border + check icon. Reading/Gardening from the wireflow become editable in "My interests".

### 5.10 Forms
- Labels above fields, always visible (no placeholder-only labels). Help text under the label. Inline validation after blur, with errors summarized at the top for screen readers.
- Use native inputs for date/time where possible; supplement with text input examples ("Example: 11/05/2026").

---

## 6. Key flows

### 6.1 Story 14 — Personalized recommendations
1. **Home:** greeting by time of day, headline, one clear action "Find something for me", interests shown below as editable tags.
2. **Preferences:** assistant asks "What kind of activity would feel good today?" with quick replies (Online, In person, Morning, Afternoon, Evening, Quiet, Social). Earlier-conversation memory shown as a removable chip. Checkbox for using earlier conversations. Button: "Find suggestions".
3. **Suggestions:** "A good place to begin." One hero recommendation, up to 2 secondary cards, one resource card, then the context strip (see 4.3 and 5.5).
4. **Source check:** source quote, record ID, "How your preferences were used", Back.

Improvements over the wireflow: "Refine my suggestions" is a full button; "Not for me" with Undo on each card; an in-person path (distance, accessibility details, transport help).

### 6.2 Story 13 — Programs to calendar
1. **Ask in Assistant** → assistant proposes a saved list; nothing created yet.
2. **Select programs** → checkboxes, "Review N events".
3. **Review and permission** → consent checkbox, reminders (1 day before, 30 minutes before), time zone, one-time only.
4. **Created** → success summary, what was not created, reminder-is-not-registration notice.

Additions: reminder choices beyond the defaults ("Morning of", "1 hour before"); ".ics download" and "Email me the details" for people who don't use a calendar app; a caregiver/family contact receives reminders **only with the user's explicit opt-in**.

### 6.3 Daily journal and wellbeing check-in
- **Daily prompt screen:** one question at a time: "How are you feeling today?" with 5 large, labeled radio rows (Very good, Good, Okay, Not so good, Hard right now). Each row has a face icon whose mouth shape differs, plus the word, so meaning never depends on color. Selected row = thick green border, sage fill, "Selected" label. Optional note or voice note. "Save today" and "Skip today" are equal in size.
- **Journal is private by default.** State plainly who can see it (only the user) and what the assistant can use from it. Per-entry toggle: "Let the assistant use this to suggest activities."
- **Response patterns:**
  - Very good / Good / Okay → gentle activity suggestion, optionally link to saved plans.
  - Not so good → warm acknowledgment, one small step, offer of a group or a wellbeing resource.
  - Hard right now, or sustained low mood over several entries → compassionate message with resources and an option to talk to a person. No diagnostic language.
- **Crisis safeguard (non-negotiable):** if the user's language suggests risk of self-harm or crisis, the assistant shows crisis resources immediately (in the US: call or text **988**, the Suicide & Crisis Lifeline; for emergencies, 911), with a one-tap call button. These resources are also always reachable from the footer / Help tab. Content must be reviewed by a licensed mental health professional before launch.
- The assistant **never diagnoses, never replaces professional care, and says so.** Mood history is optional and simple, not scores or grades.
- No streaks, badges, or guilt for missing days. Re-entry copy: "Welcome back. Glad you're here."

### 6.4 Onboarding (recommended)
1. Welcome + "Choose your text size" (live preview) + contrast toggle.
2. "What do you enjoy?" interest picker (10–12 pill tags, multi-select, skip allowed).
3. "How would you like to meet people?" Online / In person / Both. If in person: ZIP/city, travel comfort, mobility needs (optional), transport needs.
4. Privacy choices, plain language: what is stored, what the assistant can use, how to delete data.
5. Optional trusted contact.
Total: under 5 minutes, each step skippable and revisitable from Settings.

---

## 7. Content and tone

- Warm, respectful, adult. No baby talk, no "seniors" or "elderly" in UI copy. Use "you" and "older adults" in marketing only.
- Short: one idea per sentence. Prefer concrete nouns and verbs.
- Never say "AI-powered", "smart", or "personalized for you" without saying what that means in context.
- Examples:
  - Good: "I found 3 free, online afternoon programs. You'll review the dates before I create anything."
  - Avoid: "Our AI has curated optimized recommendations for you!"
- Garden-themed language is welcome in moderation ("A good place to begin") but never at the cost of clarity. No gardening metaphors for health or mood.
- Always disclose when a response comes from the assistant versus a person on the team.
- Date format: "Thu, Nov 5, 3:00–4:00 PM Eastern" (include day name; avoid numeric-only dates).

---

## 8. RAG assistant safety and trust requirements (design-level)

- **Grounded answers only.** Group/program recommendations must come from the curated directory with a source record. If no source exists, say so ("I couldn't find a match. Here's what I can do instead").
- **Source transparency:** every recommendation links to its source; "How your preferences were used" is available on every result.
- **User control of memory:** list of what the assistant remembers ("Books", "Online afternoons"), each removable; one-tap "Forget everything".
- **Consent before action:** the assistant never creates calendar events, sends messages, or contacts anyone without the confirmation pattern in 5.7.
- **No medical, legal, or financial advice;** redirect to appropriate human resources.
- **Scam and safety awareness:** group join links are only shown from verified directory records; first-time in-person meetups show safety tips ("Meet in a public place", "Tell someone where you're going").
- **Human fallback:** "Talk to a person" available from chat, Help, the context strip, and the journal.
- **Privacy:** minimal data collection, clear retention policy, user-initiated export and deletion. Confirm legal obligations (e.g., HIPAA applicability, state privacy laws) with counsel since journal entries can be sensitive.

---

## 9. Responsive behavior summary

| Element | Mobile (≤599) | Tablet (600–1023) | Desktop (1024+) |
|---|---|---|---|
| Navigation | Floating pill bar, 5 labeled tabs | Top pill nav or bottom bar | Top pill nav with text labels |
| Home | Single column, hero + 1 action | Single column, wider cards | Hero + stacked secondary cards side by side |
| Assistant | Full-screen chat, sticky input | Full-height panel | Chat column 720px + optional side panel with sources/list |
| Recommendations | Hero first, then secondary cards stacked | Same, wider | Hero left (~58%), secondary column right |
| Context strip | Collapsible section below cards | Below cards | Full-width sage band below cards |
| Source panel | Full-screen sheet with Back | Sheet | Side panel or inline expansion |
| Review events | Stacked, sticky confirm bar | Stacked | Two-column (events left, reminders right) |

---

## 10. Open questions for the team

1. In-person discovery: what is the data source for local groups, and who verifies them?
2. Is a caregiver/family role in scope for v1?
3. Which calendar providers will we support (Google, Apple, Outlook, .ics only)?
4. Crisis-resource review: who on the team or advisory board signs off on journal and wellbeing responses?
5. Native apps vs. responsive web/PWA for v1?
6. Languages to support at launch?
7. Final product name and logo (the leaf motif and wordmark color should follow the logo once it exists).
8. Dark mode: in scope for v1, or deferred?

---

## 11. Source references
- WCAG 2.2 (W3C), including 1.4.3, 1.4.6, 1.4.10, 1.4.11, 2.4.7, 2.5.8, 3.1.5
- WAI-ARIA Authoring Practices (live regions, dialog, tabs)
- National Institute on Aging guidance on health information for older adults
- Platform guidelines: Apple Human Interface Guidelines (Dynamic Type, VoiceOver), Material 3 / Android accessibility (TalkBack, font scaling)
