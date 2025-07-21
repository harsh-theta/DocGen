# 🧠 AI Strategy for DocGen – HTML-Centric Document Automation

## Overview

DocGen is an AI-powered document generation system tailored for product managers who repeatedly produce documents with similar **structure** but different **content**. The system leverages structured HTML as the common format across parsing, generation, editing, and export.

---

## 🔁 End-to-End Flow (AI + User Interaction)

```plaintext
User Upload (DOCX/PDF)
        │
        ▼
Backend parses to structured HTML
        │
        ▼
HTML rendered in WYSIWYG Editor (Tiptap)
        │
        ▼
User enters new context / project variables
        │
        ▼
🧠 LangGraph AI Agent (LLM-powered)
        │
        ▼
Generates new HTML content (same structure)
        │
        ▼
User edits generated HTML in editor
        │
        ▼
Final HTML exported to DOCX/PDF
```

---

## 🔍 Why HTML as the Core Format?

* ✅ **Parsing-Friendly**: Easy to convert DOCX to HTML (`python-docx`), limited support from PDFs
* ✅ **AI-Compatible**: LLMs understand and generate structured HTML reliably
* ✅ **Editor-Compatible**: Tiptap renders HTML, supports headings, tables, lists, and inline styles
* ✅ **Exportable**: HTML can be converted to DOCX (`html2docx`) or PDF (`weasyprint` or `puppeteer`)

---

## 🧠 AI Generation Strategy (via LangGraph)

### Input to Agent:

* `html_template`: parsed structure from uploaded sample
* `project_variables`: user-provided parameters for customization (e.g., frontend = "Next.js")

### Output from Agent:

* `generated_html`: same structure, regenerated content in HTML format

### Agent Nodes:

* **ParseNode**: Ingests the HTML template, segments into sections
* **PromptMapperNode**: Maps user variables to prompt templates
* **GeneratorNode**: Calls LLM with structured prompts (e.g., "Regenerate this section using frontend = Next.js")
* **ValidatorNode**: Optional rules to verify HTML validity
* **AssemblerNode**: Reconstructs the full document in HTML

---

## 📦 Database Schema (AI-Related Fields)

| Field            | Description                          |
| ---------------- | ------------------------------------ |
| `html_template`  | Initial parsed HTML from upload      |
| `ai_content`     | Generated HTML by the LLM            |
| `edited_html`    | Final user-edited version of content |
| `final_docx_url` | URL of exported DOCX from HTML       |
| `final_pdf_url`  | URL of exported PDF from HTML        |

---

## 🧪 Example Prompt to LLM

```text
Here is the reference section in HTML:
<h2>Tech Stack</h2>
<table>
  <tr><td>Frontend</td><td>React</td></tr>
  <tr><td>Backend</td><td>FastAPI</td></tr>
</table>

Now, regenerate this section for:
Frontend = "Next.js"
Backend = "Node.js"
```

---

## ✅ Advantages of This Approach

* Unified format for input/output/edit/export
* Better LLM accuracy with structured inputs
* Easy to render and edit with modern frontend tooling
* Portable across document formats

---