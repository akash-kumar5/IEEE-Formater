import streamlit as st
from openai import OpenAI
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from io import BytesIO
import re

# === API Setup ===
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

# === AI Formatter ===
def gpt_fix_sections(text):
    prompt = f"""
You are an academic formatting assistant.

Format the following engineering project report text into **IEEE conference paper format**.

Apply all the following formatting rules:

---

📝 General Formatting:
- Font: Times New Roman
- Font Size: 10 pt
- Line spacing: Single
- Justification: Fully justified
- Margins: 1 inch (A4 paper)
- No page numbers, headers, or footers

---

📌 Title & Author:
- Title: Centered, bold, title case (no subtitle)
- Author block includes: Name, Department, Institute, City, Country, Email/ORCID
- No more than 6 authors per row

---

📃 Abstract & Keywords:
- Start with "Abstract—" in italics, followed by the abstract
- Below it, "Keywords—" in italics, followed by comma-separated list

---

📚 Headings:
- Heading 1: Bold, ALL CAPS, numbered (e.g., "I. INTRODUCTION")
- Heading 2: Italic, Capitalized, lettered (e.g., "A. Method Overview")
- Heading 3: Italic, inline with paragraph (e.g., "1) Sample Prep")
- Heading 4: Italic, lead-in for paragraph (e.g., "a) Setup:")

---

🧮 Equations:
- Centered, equation numbers right-aligned in parentheses: (1)
- Roman variables in italics; Greek not italicized
- No "Eq. (1)" in-line — say "(1)" or "Equation (1)"

---

📊 Figures & Tables:
- Figures: Caption below as "Fig. X. Description", font size 8 pt
- Tables: Caption above as "TABLE X. TITLE"
- Axis must use full labels: e.g., "Current (A)" not just "A"

---

📐 Units:
- Use SI (MKS) or CGS units, not mixed
- Add 0 before decimal: "0.5", not ".5"
- Do not mix full-word and unit formats

---

✏️ Writing Style Rules:
- "Data" is plural
- Use "et al." properly
- "i.e." = that is, "e.g." = for example
- No space in prefixes: use "nonlinear", not "non linear"
- Use "affect/effect", "principle/principal" correctly

---

🔖 References:
- Use square brackets for citation: [1], [2]
- In-text: "...as shown in [1]" or "Reference [2] demonstrates..."
- Format: [1] Author(s), *Title*, Publisher, Year, Pages.
- Capitalize only the first word in paper titles (except proper nouns)

---

Now format the following text into a clean IEEE-style version, applying all above rules strictly.

Text:
{text}
"""
    try:
        completion = client.chat.completions.create(
            model="deepseek/deepseek-r1-0528:free",
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error: {e}"

# === Docx Export ===
def is_ieee_heading(line):
    return re.match(r"^[IVXLCDM]+\.\s+[A-Z][A-Z0-9\s\-&]+$", line.strip()) is not None

def create_formatted_docx(text):
    doc = Document()

    # 1-inch margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Group lines into paragraphs
    lines = text.strip().split("\n")
    buffer = []
    
    def add_paragraph(block):
        block = " ".join(block).strip()
        if not block:
            return
        if is_ieee_heading(block):
            para = doc.add_paragraph()
            run = para.add_run(block.upper())
            run.bold = True
            run.font.name = 'Times New Roman'
            run.font.size = Pt(10)
            para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
        else:
            para = doc.add_paragraph()
            run = para.add_run(block)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(10)
            para.paragraph_format.line_spacing = 1.0
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.first_line_indent = Pt(0)
            para.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

    for line in lines:
        if line.strip() == "":
            add_paragraph(buffer)
            buffer = []
        else:
            buffer.append(line.strip())
    if buffer:
        add_paragraph(buffer)

    return doc



def clean_model_output(text):
    text = re.sub(r"(?<!\w)\*{1,2}([^\*]+?)\*{1,2}(?!\w)", r"\1", text)  # Remove *italic* or **bold**
    text = re.sub(r"^[-–•]+\s*", "", text, flags=re.MULTILINE)  # Remove bullets
    text = re.sub(r"\n{3,}", "\n\n", text)  # Collapse 3+ newlines to 2
    text = re.sub(r"—{2,}", "", text)  # Remove long markdown dividers
    text = text.strip()
    return text

# === Streamlit UI ===
st.title("📄 IEEE Report Formatter")

uploaded_file = st.file_uploader("Upload your .docx file", type=["docx"])

if uploaded_file and "formatted_text" not in st.session_state:
    st.success("File uploaded successfully!")

    # Extract text
    original_doc = Document(uploaded_file)
    full_text = "\n".join([p.text for p in original_doc.paragraphs if p.text.strip()])

    # AI formatting
    with st.spinner("Formatting with AI..."):
        raw_formatted = gpt_fix_sections(full_text)
        cleaned = clean_model_output(raw_formatted)
        st.session_state.formatted_text = cleaned

    if "⚠️ Error" in st.session_state.formatted_text:
        st.error(st.session_state.formatted_text)
    else:
        if "formatted_text" in st.session_state:
            st.subheader("📘 Formatted Preview")
            st.session_state.formatted_text = clean_model_output(st.session_state.formatted_text)
            st.text_area("Output", st.session_state.formatted_text, height=400)

            # Generate .docx
            doc = create_formatted_docx(st.session_state.formatted_text)
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)

            st.download_button("⬇ Download Formatted DOCX", buffer, file_name="ieee_formatted.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

