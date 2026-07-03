# Reply Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a `reply-generator` skill that uses externalized reply templates and context-aware tone matching to generate low-AI-flavor replies.

**Architecture:** Add a new skill directory with one `SKILL.md` for workflow rules and a `references/` tree for template lookup, style mapping, and examples. Keep the implementation document-driven, with no runtime scripts, and update the repository README so the new skill is installable and discoverable.

**Tech Stack:** Markdown skill files, repository README

## Global Constraints

- Follow the approved spec in `docs/superpowers/specs/2026-07-03-reply-generator-design.md`.
- Keep edits minimal and scoped to the new `reply-generator` skill plus the related README entry.
- Do not touch third-party skill descriptions in `README.md`.
- Do not add automated tests; the user explicitly said tests are not needed.
- README install examples must stay portable and must not use personal absolute paths.

---

### Task 1: Create the skill skeleton and main workflow

**Files:**
- Create: `skills/reply-generator/SKILL.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-07-03-reply-generator-design.md`
- Produces: `reply-generator` trigger description, workflow rules, output format, and reference-loading instructions

- [ ] **Step 1: Create `skills/reply-generator/SKILL.md`**

Write a new skill file with:
- YAML frontmatter:
  - `name: reply-generator`
  - a trigger description covering reply generation, tone imitation, template-based replies, and low-AI-flavor output
- sections for:
  - when to use
  - input extraction order
  - template selection rules
  - context imitation rules
  - output format
  - exception handling
  - reference files to read on demand

- [ ] **Step 2: Verify the file exists and has the required headings**

Run: `rg -n "^---$|^name: reply-generator|^## " skills/reply-generator/SKILL.md`
Expected: frontmatter plus the major workflow headings are present

### Task 2: Create references and initial templates

**Files:**
- Create: `skills/reply-generator/references/INDEX.md`
- Create: `skills/reply-generator/references/style-mapping.md`
- Create: `skills/reply-generator/references/examples.md`
- Create: `skills/reply-generator/references/templates/jiahao.md`
- Create: `skills/reply-generator/references/templates/restrained-workplace.md`
- Create: `skills/reply-generator/references/templates/sarcastic-light.md`
- Create: `skills/reply-generator/references/templates/friendly-banters.md`

**Interfaces:**
- Consumes: `skills/reply-generator/SKILL.md`
- Produces: template metadata, style word mapping, examples, and four starter template definitions

- [ ] **Step 1: Create the references index**

Write `references/INDEX.md` as a compact table of template names, aliases, scenarios, style tags, and file paths.

- [ ] **Step 2: Create the style mapping rules**

Write `references/style-mapping.md` with natural-language style phrases mapped to a primary template, fallback template, and usage note.

- [ ] **Step 3: Create the examples file**

Write `references/examples.md` with concise input/output examples covering chat, workplace, light sarcasm, and low-context fallback.

- [ ] **Step 4: Create the four starter template files**

Each template file must include:
- positioning
- suitable / unsuitable scenarios
- tone traits
- rhythm and length
- sentence skeletons
- preferred expressions
- banned expressions
- generation constraints
- examples

- [ ] **Step 5: Verify the reference tree**

Run: `find skills/reply-generator -maxdepth 3 -type f | sort`
Expected: `SKILL.md`, `references/INDEX.md`, `style-mapping.md`, `examples.md`, and four template files

### Task 3: Update repository documentation

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `skills/reply-generator/SKILL.md`, `skills/reply-generator/references/INDEX.md`
- Produces: a new README section with install command, feature summary, and usage examples

- [ ] **Step 1: Add the `reply-generator` section to `README.md`**

Insert a new section in the Skills List with:
- one-line description
- install command: `npx skills add xiyueyezibile/xiy-skills@reply-generator -g -y`
- short feature bullets
- a few example prompts

- [ ] **Step 2: Verify the README entry**

Run: `rg -n "reply-generator|xiyueyezibile/xiy-skills@reply-generator" README.md`
Expected: the new section and install command are present

### Task 4: Final review and workspace verification

**Files:**
- Review: `skills/reply-generator/SKILL.md`
- Review: `skills/reply-generator/references/*`
- Review: `README.md`

**Interfaces:**
- Consumes: all edits from Tasks 1-3
- Produces: verified file inventory and diff summary

- [ ] **Step 1: Review the created files for consistency**

Check that:
- template names in `INDEX.md` match actual filenames
- `SKILL.md` references only existing files
- README wording matches the new skill behavior

- [ ] **Step 2: Run final verification commands**

Run: `find skills/reply-generator -maxdepth 3 -type f | sort && echo '---' && rg -n "reply-generator|xiyueyezibile/xiy-skills@reply-generator" README.md`
Expected: all new files are listed and the README entry is present

- [ ] **Step 3: Review git status**

Run: `git status --short`
Expected: only the intended new skill files, plan/spec docs, summary update, and README changes appear
