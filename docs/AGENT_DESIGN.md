# 🧠 DocGen AI Workflow Strategy (LangGraph + Gemini)

## Overview

The DocGen system automates the generation of structured documents (e.g., for product managers) by reusing the **format** of a reference document while fully regenerating the **content** based on a new project prompt. This strategy outlines how we’ll use LangGraph and Gemini LLM in a **section-by-section workflow** for predictable and scalable AI generation.

---

## 🎯 Goals

* Maintain **consistent structure** (from uploaded DOCX/PDF parsed into HTML)
* Regenerate **all content** from a new project context
* Require **minimal manual input** from the user
* Keep the system **modular, testable, and resilient**

---

## 🧩 Input Model

Users will provide the following:

### 1. **Natural Language Prompt**

A detailed project description written freely by the user.

### 2. **Strict Variables (Explicit Fields)**

Separate fields for:

```json
{
  "project_name": "ZenFlow",
  "project_description": "An internal HR automation tool for onboarding"
}
```

### 3. **Optional JSON Overrides (Inline in Prompt)**

Advanced users can optionally include strict overrides at the end of the prompt:

```text
We're building a fintech app called FinStack...

{
  "frontend": "Next.js",
  "auth_method": "OAuth2"
}
```

---

## 📥 Unified Input Schema to LangGraph

```json
{
  "html_template": "<html>...</html>",
  "prompt_text": "Long prompt text including optional JSON",
  "strict_vars": {
    "project_name": "FinStack",
    "project_description": "A tax automation tool for crypto users"
  }
}
```

---

## 🧠 Why Section-by-Section Generation?

* ✅ **Smaller prompts** → better LLM accuracy
* ✅ **Modular retry/fallback logic**
* ✅ **Matches structure of parsed HTML**
* ✅ **Clean orchestration with LangGraph workflow nodes**
* ✅ **Better UX for future features like per-section editing or review**

---

## 🧱 LangGraph Workflow Design

### Node-Level Breakdown:

```plaintext
Start
  │
  ▼
ParseTemplateNode  → Extracts sections from HTML
  │
  ▼
ForEachSectionNode → Loops through section blocks
  │
  ▼
GenerateSectionNode → Calls Gemini with structured prompt
  │
  ▼
MergeNode → Reassembles final HTML
  │
  ▼
Output: Full Generated HTML Document
```

### Optional Nodes:

* `DefaultFillerNode`: For missing prompt info
* `ValidatorNode`: Ensures clean HTML output

---

## 🔄 Per Section Generation Logic

Each section receives:

```json
{
  "section_html": "<h2>Tech Stack</h2><table>...</table>",
  "prompt_text": "...",
  "strict_vars": { ... },
  "json_overrides": { ... }
}
```

### Prompt to Gemini:

```text
Rewrite the following document section using the new project context.

Original:
<h2>Tech Stack</h2>
<table>...</table>

Context:
Project name: ZenFlow
Project description: An HR automation tool

User prompt:
"We're building a tool called ZenFlow to simplify onboarding..."

Overrides:
{ "frontend": "Svelte", "backend": "Django" }

Regenerate this section accordingly.
```

---

## 🧪 Benefits

| Area          | Benefit                                               |
| ------------- | ----------------------------------------------------- |
| Prompt Design | Natural and flexible for users                        |
| Agent Design  | Simple, workflow-based, and stateless per section     |
| Resilience    | Easy fallback or placeholder handling                 |
| Performance   | Small LLM calls vs one giant blob prompt              |
| Extensibility | Easy to insert validation, reruns, or UI review later |

---

## ✅ Summary

We’ve finalized a strategy that is:

* ✨ Intuitive for users
* 🧠 AI-optimized for clarity and performance
* 🏗️ Developer-friendly and modular
* 🚀 Ready to be implemented step-by-step via LangGraph + Gemini

---