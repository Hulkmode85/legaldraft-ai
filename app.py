import os
from flask import Flask, request, render_template_string, jsonify
import anthropic

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

DOC_TYPES = {
    "nda": {"name": "Non-Disclosure Agreement (NDA)", "fields": ["Party 1 Name", "Party 2 Name", "Purpose/Context", "Duration (e.g., 2 years)", "Jurisdiction/State"]},
    "tos": {"name": "Terms of Service", "fields": ["Company/Website Name", "Website URL", "Type of Service", "Jurisdiction/State"]},
    "privacy": {"name": "Privacy Policy", "fields": ["Company/Website Name", "Website URL", "Data Collected (e.g., email, name, payment)", "Third-party Services Used", "Jurisdiction/State"]},
    "freelancer": {"name": "Freelancer Contract", "fields": ["Client Name", "Freelancer Name", "Project Description", "Payment Amount", "Payment Terms", "Deadline", "Jurisdiction/State"]},
    "rental": {"name": "Rental Agreement", "fields": ["Landlord Name", "Tenant Name", "Property Address", "Monthly Rent", "Lease Start Date", "Lease Duration", "Security Deposit", "Jurisdiction/State"]},
}

FORM_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LegalDraft AI - Legal Document Generator</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh}
.container{max-width:900px;margin:0 auto;padding:40px 20px}
h1{font-size:2.2rem;background:linear-gradient(135deg,#8b5cf6,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
p.sub{color:#888;margin-bottom:30px;font-size:1.05rem}
.disclaimer{background:#1a1520;border:1px solid #8b5cf6;border-radius:8px;padding:16px;margin-bottom:24px;color:#c4b5fd;font-size:.9rem}
.doc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px;margin-bottom:30px}
.doc-card{background:#151515;border:1px solid #222;border-radius:12px;padding:20px;cursor:pointer;transition:all .2s}
.doc-card:hover,.doc-card.active{border-color:#8b5cf6;background:#1a1520}
.doc-card h3{color:#c4b5fd;margin-bottom:6px;font-size:1rem}
.doc-card p{color:#666;font-size:.85rem}
#fields-form{background:#151515;border:1px solid #222;border-radius:12px;padding:30px;display:none}
label{display:block;margin-bottom:6px;color:#aaa;font-size:.9rem;margin-top:16px}
label:first-child{margin-top:0}
input,textarea{width:100%;padding:12px;background:#0a0a0a;border:1px solid #333;border-radius:8px;color:#fff;font-size:1rem}
textarea{height:100px;resize:vertical}
button{width:100%;padding:14px;background:linear-gradient(135deg,#8b5cf6,#ec4899);border:none;border-radius:8px;color:#fff;font-size:1.1rem;cursor:pointer;font-weight:600;margin-top:24px}
button:hover{opacity:.9}
.loading{display:none;text-align:center;padding:20px;color:#8b5cf6}
.badge{display:inline-block;background:#8b5cf6;color:#fff;padding:4px 12px;border-radius:20px;font-size:.8rem;margin-bottom:16px}
</style>
</head>
<body>
<div class="container">
<span class="badge">AI Legal Documents</span>
<h1>LegalDraft AI</h1>
<p class="sub">Generate professional legal documents in minutes. Select a template, fill in details, done.</p>
<div class="disclaimer">This tool generates legal document drafts for informational purposes only. This is NOT legal advice. Always consult a qualified attorney before signing or relying on any legal document.</div>

<h2 style="color:#c4b5fd;margin-bottom:16px;font-size:1.1rem">1. Select Document Type</h2>
<div class="doc-grid">
""" + "".join(f'''<div class="doc-card" onclick="selectDoc('{k}')"><h3>{v['name']}</h3><p>{len(v['fields'])} fields to fill</p></div>''' for k, v in DOC_TYPES.items()) + """
</div>

<form id="fields-form" method="POST" action="/generate" onsubmit="document.getElementById('load').style.display='block'">
<h2 style="color:#c4b5fd;margin-bottom:16px;font-size:1.1rem">2. Fill in Details</h2>
<input type="hidden" name="doc_type" id="doc_type_input">
<div id="dynamic-fields"></div>
<label>Additional Instructions (optional)</label>
<textarea name="extra" placeholder="Any special clauses, modifications, or context..."></textarea>
<button type="submit">Generate Document</button>
</form>
<div id="load" class="loading">Drafting your document...</div>
</div>
<script>
const docTypes = """ + str({k: v for k, v in DOC_TYPES.items()}).replace("'", '"') + """;
function selectDoc(type) {
    document.querySelectorAll('.doc-card').forEach(c => c.classList.remove('active'));
    event.currentTarget.classList.add('active');
    document.getElementById('doc_type_input').value = type;
    const fields = docTypes[type].fields;
    let html = '';
    fields.forEach(f => {
        const name = f.toLowerCase().replace(/[^a-z0-9]/g, '_');
        html += '<label>' + f + '</label><input type="text" name="field_' + name + '" placeholder="' + f + '" required>';
    });
    document.getElementById('dynamic-fields').innerHTML = html;
    document.getElementById('fields-form').style.display = 'block';
}
</script>
</body>
</html>
"""

RESULT_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Your Document - LegalDraft AI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh}
.container{max-width:900px;margin:0 auto;padding:40px 20px}
h1{font-size:1.8rem;background:linear-gradient(135deg,#8b5cf6,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:20px}
.disclaimer{background:#1a1520;border:1px solid #8b5cf6;border-radius:8px;padding:16px;margin-bottom:24px;color:#c4b5fd;font-size:.9rem}
.document{background:#151515;border:1px solid #222;border-radius:12px;padding:30px;line-height:1.8;white-space:pre-wrap;font-size:1rem}
.copy-btn{display:inline-block;margin-top:16px;padding:10px 24px;background:linear-gradient(135deg,#8b5cf6,#ec4899);border:none;border-radius:8px;color:#fff;cursor:pointer;font-size:.95rem;font-weight:600}
.copy-btn:hover{opacity:.9}
a{color:#8b5cf6;text-decoration:none}
.back{display:inline-block;margin-top:20px}
</style>
</head>
<body>
<div class="container">
<h1>{{ doc_name }}</h1>
<div class="disclaimer">DISCLAIMER: This document is AI-generated for informational purposes only. It does NOT constitute legal advice. Consult a qualified attorney before signing or relying on this document.</div>
<div class="document" id="doc">{{ document }}</div>
<button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('doc').textContent);this.textContent='Copied!'">Copy to Clipboard</button>
<br><a class="back" href="/">&#8592; Generate Another Document</a>
</div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(FORM_PAGE)

@app.route("/generate", methods=["POST"])
def generate():
    doc_type = request.form.get("doc_type", "")
    extra = request.form.get("extra", "").strip()

    if doc_type not in DOC_TYPES:
        return "Invalid document type.", 400

    doc_info = DOC_TYPES[doc_type]
    fields = {}
    for f in doc_info["fields"]:
        key = "field_" + f.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").replace(",", "").replace(".", "")
        # Try multiple key formats
        val = request.form.get(key, "")
        if not val:
            # Try with the simpler sanitization matching the JS
            import re
            simple_key = "field_" + re.sub(r'[^a-z0-9]', '_', f.lower())
            val = request.form.get(simple_key, "")
        fields[f] = val

    fields_text = "\n".join(f"- {k}: {v}" for k, v in fields.items() if v)
    extra_text = f"\nAdditional instructions: {extra}" if extra else ""

    prompt = f"""Generate a complete, professional {doc_info['name']} legal document based on these details:

{fields_text}
{extra_text}

Requirements:
- Use formal legal language appropriate for a real document
- Include all standard clauses for this document type
- Include signature blocks at the end
- Include the date
- Be thorough and comprehensive — this should be a complete, usable draft
- Format clearly with numbered sections

IMPORTANT: Add this disclaimer at the very top:
"DRAFT DOCUMENT - FOR INFORMATIONAL PURPOSES ONLY. NOT LEGAL ADVICE. CONSULT AN ATTORNEY BEFORE USE."

Generate the full document now."""

    msg = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    document = msg.content[0].text

    return render_template_string(RESULT_PAGE, doc_name=doc_info["name"], document=document)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "LegalDraft AI"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
