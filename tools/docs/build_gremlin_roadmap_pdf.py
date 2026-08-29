from pathlib import Path
import mistune
from weasyprint import HTML, CSS

ROOT = Path(__file__).resolve().parents[2]
MD = ROOT / "docs/roadmap/GREMLIN_DEVELOPMENT_ROADMAP_V0_1.md"
PDF = ROOT / "docs/roadmap/GREMLIN_DEVELOPMENT_ROADMAP_V0_1.pdf"

text = MD.read_text(encoding="utf-8")
lines = text.splitlines()
body_md = "\n".join(lines[6:] if len(lines) > 6 else lines)
markdown = mistune.create_markdown(plugins=["table", "strikethrough"])
body_html = markdown(body_md)

cover = """
<section class="cover">
  <div class="eyebrow">GREMLIN / DEVELOPMENT ROADMAP</div>
  <h1>GREMLIN Development Roadmap</h1>
  <div class="version">v0.1 · 2026-08-29</div>
  <p class="lead">From standalone Bestiary/MCP to a source-typed semantic-orbital runtime with auditable routing, C7 phase geometry, role-typed orbital dynamics, RFC source binding, PNLF memory integration and bounded HTRI/QHTRI actuation.</p>
  <div class="cover-grid">
    <div class="cover-card"><span>Repository</span><strong>AdrianLipa90/GREMLIN</strong></div>
    <div class="cover-card"><span>Verified main at drafting</span><strong>a35f2a8c6b5d…</strong></div>
    <div class="cover-card"><span>Current operational base</span><strong>MCP v0.4 standalone Bestiary</strong></div>
    <div class="cover-card"><span>Research frontier</span><strong>Semantic orbitals + mass-role scheduler</strong></div>
  </div>
  <div class="formula">
    <div>kappa = ln(2)/(24*pi)</div>
    <div>omega^2 = (mu_source/r^3) * (q_coupling/m_inertial)</div>
    <div>G(t) = [B*omega*N/(A*R)] * (phi_tilde + kappa)</div>
  </div>
  <div class="status">WORKING_ROADMAP · EVIDENCE-FIRST · CANDIDATE-AWARE</div>
</section>
"""

html = f"<!doctype html><html><head><meta charset='utf-8'></head><body>{cover}<main>{body_html}</main></body></html>"

css = CSS(string=r"""
@page {
  size: A4;
  margin: 18mm 18mm 20mm 18mm;
  @bottom-left { content: "GREMLIN Development Roadmap v0.1"; color: #687386; font-size: 8pt; }
  @bottom-right { content: "Page " counter(page) " / " counter(pages); color: #687386; font-size: 8pt; }
}
@page:first { margin: 0; @bottom-left { content: none; } @bottom-right { content: none; } }
* { box-sizing: border-box; }
body { font-family: sans-serif; color: #18202b; font-size: 9.4pt; line-height: 1.46; }
.cover { height: 297mm; padding: 28mm 24mm; page-break-after: always; background: #132238; color: #f4f7fb; position: relative; }
.eyebrow { color: #8edccf; font-size: 9pt; font-weight: 700; letter-spacing: 2.2px; margin-bottom: 20mm; }
.cover h1 { font-size: 31pt; line-height: 1.05; margin: 0 0 5mm 0; max-width: 150mm; }
.version { font-size: 13pt; color: #b8c7d9; margin-bottom: 13mm; }
.lead { max-width: 150mm; font-size: 12pt; line-height: 1.55; color: #dbe5ef; margin-bottom: 14mm; }
.cover-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; max-width: 160mm; }
.cover-card { background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.15); padding: 5mm; border-radius: 3mm; }
.cover-card span { display: block; color: #9cb1c7; font-size: 8pt; margin-bottom: 2mm; }
.cover-card strong { font-size: 10pt; color: #f5f9fc; }
.formula { margin-top: 13mm; max-width: 150mm; padding: 5mm 6mm; border-left: 4px solid #8edccf; background: rgba(0,0,0,.14); font-family: monospace; font-size: 9pt; line-height: 1.8; }
.status { position: absolute; bottom: 23mm; left: 24mm; font-size: 8pt; letter-spacing: 1px; color: #91a8bd; }
h2 { color: #173653; font-size: 18pt; margin: 8mm 0 4mm 0; padding-bottom: 2mm; border-bottom: 2px solid #b8d8d2; page-break-after: avoid; }
h3 { color: #24536e; font-size: 12.5pt; margin: 5.5mm 0 2mm 0; page-break-after: avoid; }
p { margin: 0 0 3mm 0; orphans: 3; widows: 3; }
ul, ol { margin: 2mm 0 4mm 6mm; padding-left: 4mm; }
li { margin: 1.2mm 0; }
strong { color: #0d2b43; }
code { font-family: monospace; font-size: 8.3pt; background: #edf3f6; color: #15384e; padding: 1px 3px; border-radius: 2px; }
table { border-collapse: collapse; width: 100%; margin: 4mm 0 6mm 0; font-size: 8.3pt; page-break-inside: avoid; }
th { background: #173653; color: white; text-align: left; font-weight: 700; padding: 2.3mm; }
td { border-bottom: 1px solid #d7e0e7; padding: 2.2mm 2.3mm; vertical-align: top; }
tr:nth-child(even) td { background: #f6f9fb; }
hr { border: none; border-top: 1px solid #d6e0e7; margin: 7mm 0; }
""")

PDF.parent.mkdir(parents=True, exist_ok=True)
HTML(string=html, base_url=str(ROOT)).write_pdf(str(PDF), stylesheets=[css])
print(PDF)
