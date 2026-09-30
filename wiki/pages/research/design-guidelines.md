---
created: 2026-09-30
type: research
summary: UI/UX design guidelines — tone, color palette, typography, components, and Git visual language.
---

# Design Guidelines

The UI should feel:

Clean — lots of white space and simple layouts
Trustworthy — Git/developer-tool aesthetic without looking overly technical
Friendly — use color and rounded details to make documentation approachable
Content-first — the wiki content is always more important than decoration
2. Color palette
Primary
Color	Hex	Use
Giiki Navy	#14213D	Main text, headings, navigation
White	#FFFFFF	Main background
Soft Gray	#F5F7FA	Cards, panels, secondary backgrounds
Border Gray	#E2E8F0	Borders, dividers
Brand accents
Color	Hex	Use
Git Red	#FF3B30	Brand emphasis, important actions, Git-related elements
Giiki Blue	#1677FF	Links, primary interactive elements, selected navigation
Giiki Orange	#FF9F1C	Secondary actions, highlights, status/category accents
Color principle

Use Navy + White + one accent for most screens.

Red, blue, and orange should not compete with each other. They are functional accents:

🔵 Blue → interaction, links, navigation, selected state
🔴 Red → Git/source-of-truth concepts, important states
🟠 Orange → highlights, secondary categories, discovery

Avoid large areas of saturated color. The brand should remain predominantly white and navy.

3. Typography

Use a modern sans-serif such as Inter.

Recommended hierarchy:

H1: 32–40px, semibold/bold
H2: 24–28px, semibold
H3: 18–20px, semibold
Body: 15–16px, regular
Small/meta: 13–14px

Headings use Giiki Navy.
Body text can use a softer dark gray such as #475569.

Keep line lengths comfortable for documentation: approximately 65–80 characters per line.

4. UI components
Buttons

Primary button:

Blue #1677FF
White text
6–8px border radius

Secondary button:

White background
Navy text
Gray border

Destructive actions:

Git Red #FF3B30
Cards

Use:

White background
#E2E8F0 border
8–12px radius
Very subtle shadow, if necessary

Cards should support the content, not make the interface look like a dashboard full of boxes.

Navigation

Keep navigation quiet and predictable.

Default: Navy/dark gray icons and text
Hover: light blue background
Active: blue text + very light blue background
Git/source indicators: red
5. Wiki pages

Wiki pages should be mostly white.

Use color sparingly for:

Links
Code blocks
Callouts
Tags
Status indicators
Git/version information

The reading experience should resemble a high-quality technical documentation site rather than a colorful SaaS dashboard.

6. Git visual language

Git should have a recognizable but secondary visual identity.

Use the red Git accent for:

Repository information
Commit/version indicators
"Synced from Git" status
Git source badges

Example:

Git repository → 🔴
Wiki page → 🔵
Documentation category → 🟠