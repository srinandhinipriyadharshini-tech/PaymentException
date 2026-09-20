from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "UC02_Core_Payment_Exceptions_Pitch.pptx"

NAVY = RGBColor(7, 17, 28)
NAVY_2 = RGBColor(12, 29, 43)
PANEL = RGBColor(15, 39, 55)
PANEL_2 = RGBColor(20, 51, 67)
WHITE = RGBColor(237, 246, 248)
MUTED = RGBColor(151, 177, 188)
CYAN = RGBColor(88, 212, 205)
CORAL = RGBColor(240, 111, 94)
AMBER = RGBColor(234, 183, 106)
RED = RGBColor(239, 116, 124)
LILAC = RGBColor(156, 140, 245)
LINE = RGBColor(43, 73, 88)


def add_box(slide, x, y, w, h, fill=PANEL, line=LINE, radius=True):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid(); shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line; shape.line.width = Pt(0.8)
    return shape


def add_text(slide, text, x, y, w, h, size=14, color=WHITE, bold=False, font="Aptos", align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame; frame.clear(); frame.word_wrap = True; frame.vertical_anchor = valign
    para = frame.paragraphs[0]; para.alignment = align
    run = para.add_run(); run.text = text; run.font.name = font; run.font.size = Pt(size); run.font.bold = bold; run.font.color.rgb = color
    return box


def add_bullets(slide, items, x, y, w, h, size=15, color=WHITE):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame; frame.clear(); frame.word_wrap = True
    for index, item in enumerate(items):
        para = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        para.text = item; para.level = 0; para.font.name = "Aptos"; para.font.size = Pt(size); para.font.color.rgb = color; para.space_after = Pt(9)
    return box


def add_title(slide, kicker, title, subtitle=None):
    add_text(slide, kicker.upper(), 0.65, 0.38, 8.5, 0.25, 9, CYAN, True, "Aptos")
    add_text(slide, title, 0.65, 0.75, 11.2, 0.6, 27, WHITE, True, "Aptos Display")
    if subtitle: add_text(slide, subtitle, 0.67, 1.39, 11.3, 0.35, 11, MUTED)


def add_footer(slide, number):
    add_text(slide, "CLEARLINE  /  UC-02", 0.65, 7.15, 3, 0.2, 8, MUTED, True)
    add_text(slide, f"0{number}  /  07", 11.75, 7.15, 1, 0.2, 8, MUTED, True, align=PP_ALIGN.RIGHT)


def add_base(prs, number, kicker, title, subtitle=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6]); slide.background.fill.solid(); slide.background.fill.fore_color.rgb = NAVY
    # Quiet grid for an operations-console feel.
    for x in range(0, 14, 1):
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(0), Inches(0.006), Inches(7.5)); line.fill.solid(); line.fill.fore_color.rgb = RGBColor(12, 34, 48); line.line.fill.background()
    for y in range(0, 8, 1):
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(y), Inches(13.333), Inches(0.006)); line.fill.solid(); line.fill.fore_color.rgb = RGBColor(12, 34, 48); line.line.fill.background()
    add_title(slide, kicker, title, subtitle); add_footer(slide, number); return slide


def pill(slide, text, x, y, w, color):
    add_box(slide, x, y, w, 0.32, fill=color, line=color)
    add_text(slide, text, x, y + 0.055, w, 0.18, 8, NAVY, True, align=PP_ALIGN.CENTER)


def slide_1(prs):
    s = add_base(prs, 1, "The problem", "Payment exceptions are a translation problem", "A customer story must become a rail-specific, deadline-aware decision.")
    add_box(s, .65, 2.05, 5.1, 4.55, NAVY_2)
    add_text(s, "CUSTOMER NARRATIVE", .95, 2.35, 2.4, .25, 9, CORAL, True)
    add_box(s, .95, 2.85, 4.3, 1.05, fill=RGBColor(34, 54, 68), line=RGBColor(60, 88, 99))
    add_text(s, '"About 8k to the plumber last Tuesday."', 1.2, 3.08, 3.8, .5, 19, WHITE, True)
    add_text(s, "Free text", 1.0, 4.45, 1.2, .25, 10, MUTED, True)
    add_text(s, "amount? date? beneficiary? rail? reason?", 2.0, 4.45, 3.1, .25, 11, WHITE)
    add_text(s, "Manual path", 1.0, 5.15, 1.2, .25, 10, MUTED, True)
    add_text(s, "search ledger -> identify payment -> apply policy -> meet deadline", 2.0, 5.15, 3.2, .5, 11, WHITE)
    add_box(s, 6.15, 2.05, 6.5, 4.55, NAVY_2)
    add_text(s, "FOUR RAILS. FOUR DECISION CONTEXTS.", 6.45, 2.35, 4.5, .25, 9, CYAN, True)
    rails = [("ACH", "return review", CYAN), ("WIRE", "investigation", AMBER), ("RTP", "finality", RED), ("FEDNOW", "finality", RED)]
    for i, (name, rule, color) in enumerate(rails):
        x = 6.45 + (i % 2) * 2.9; y = 2.95 + (i // 2) * 1.15
        add_box(s, x, y, 2.55, .85, fill=PANEL, line=LINE); add_text(s, name, x + .18, y + .15, 1, .2, 16, color, True); add_text(s, rule, x + .18, y + .48, 1.9, .18, 9, MUTED)
    for i, (value, label, color) in enumerate([("4", "rails", CYAN), ("60d", "control window", AMBER), ("6,000", "synthetic payments", LILAC), ("1", "human approval gate", CORAL)]):
        x = 6.45 + (i % 2) * 2.9; y = 5.35 + (i // 2) * .65; add_text(s, value, x, y, .8, .22, 15, color, True); add_text(s, label, x + .85, y + .02, 1.8, .2, 9, MUTED)


def slide_2(prs):
    s = add_base(prs, 2, "Architecture", "AI accelerates understanding. Rules retain authority.", "Probabilistic analysis sits inside a deterministic compliance control plane.")
    add_box(s, .65, 2.15, 5.4, 4.35, fill=RGBColor(20, 35, 57), line=RGBColor(72, 78, 130)); add_text(s, "PROBABILISTIC AI ANALYSIS", .95, 2.45, 3.7, .25, 9, LILAC, True)
    for i, text in enumerate(["IntakeAI  / extract facts", "MatchingAI  / rank candidates", "ClassificationAI  / classify intent", "DraftingAI  / explain outcome"]):
        add_box(s, .95, 2.95 + i * .7, 4.75, .48, fill=RGBColor(31, 48, 73), line=RGBColor(63, 78, 113)); add_text(s, text, 1.18, 3.08 + i * .7, 4.2, .2, 11, WHITE)
    add_box(s, 6.35, 2.15, 6.3, 4.35, fill=RGBColor(12, 48, 51), line=RGBColor(39, 127, 119)); add_text(s, "DETERMINISTIC COMPLIANCE CORE", 6.65, 2.45, 4.2, .25, 9, CYAN, True)
    for i, text in enumerate(["Step 5-6  / rail rules + deadlines", "Candidate confidence + ambiguity gates", "Human approval before submission", "Step 8  / PII masking + trace"]):
        add_box(s, 6.65, 2.95 + i * .7, 5.7, .48, fill=RGBColor(17, 68, 69), line=RGBColor(45, 126, 119)); add_text(s, text, 6.88, 3.08 + i * .7, 5.1, .2, 11, WHITE)
    add_box(s, 5.65, 3.35, 1.05, 1.05, fill=CORAL, line=CORAL); add_text(s, "AI\nrecommends", 5.65, 3.62, 1.05, .45, 10, NAVY, True, align=PP_ALIGN.CENTER)
    add_text(s, "POLICY\ndecides", 5.66, 4.6, 1.03, .4, 10, CORAL, True, align=PP_ALIGN.CENTER)


def slide_3(prs):
    s = add_base(prs, 3, "AI in action", "From “the plumber” to an evidence-backed candidate", "IntakeAI preserves uncertainty; MatchingAI makes the search explainable.")
    stages = [("01", "CUSTOMER NARRATIVE", '"I sent around eight thousand to the plumber last Tuesday."', CORAL), ("02", "STRUCTURED FACTS", "~8,000  |  beneficiary clue: plumber  |  relative date", AMBER), ("03", "OFFICIAL CANDIDATE", "John Doe Plumbing LLC\nUSD 7,950  |  96% match", CYAN)]
    for i, (num, label, text, color) in enumerate(stages):
        x = .65 + i * 4.22; add_box(s, x, 2.2, 3.65, 2.05, fill=PANEL, line=color); add_text(s, num, x + .2, 2.42, .45, .3, 19, color, True); add_text(s, label, x + .75, 2.48, 2.55, .2, 8, color, True); add_text(s, text, x + .2, 3.05, 3.15, .75, 14, WHITE, True)
        if i < 2: add_text(s, ">", x + 3.78, 3.0, .35, .35, 23, color, True, align=PP_ALIGN.CENTER)
    add_box(s, .65, 4.75, 12.0, 1.55, fill=RGBColor(5, 16, 24), line=LINE); add_text(s, "AI COGNITIVE ROUTING / REASONING TRACE", .9, 4.98, 4.2, .2, 8, CYAN, True, "DM Mono"); add_text(s, "match  ", .9, 5.38, .65, .2, 9, CYAN, True, "DM Mono"); add_text(s, "Found closest match 'John Doe Plumbing LLC' for $7,950. Date tolerance accepted (+1 day deviation).", 1.65, 5.38, 10.2, .2, 10, WHITE, False, "DM Mono"); add_text(s, "guard  ", .9, 5.78, .65, .2, 9, CYAN, True, "DM Mono"); add_text(s, "Candidate evidence is surfaced for operator review; ambiguity triggers clarification, never silent selection.", 1.65, 5.78, 10.2, .2, 10, MUTED, False, "DM Mono")


def slide_4(prs):
    s = add_base(prs, 4, "Business rules", "The clock decides what automation is allowed to do", "Deadline enforcement and rail finality are explicit, not hidden in a prompt.")
    add_box(s, .65, 2.15, 12, 2.2, fill=PANEL, line=LINE)
    add_text(s, "PAYMENT VALUE DATE", .95, 2.43, 2, .2, 8, MUTED, True); add_text(s, "DAY 0", .95, 2.78, 1, .3, 16, WHITE, True)
    add_text(s, "30 days", 3.35, 2.78, 1, .25, 13, AMBER, True); add_text(s, "ERRONEOUS", 3.25, 3.18, 1.3, .2, 8, MUTED, True)
    add_text(s, "60 days", 7.1, 2.78, 1, .25, 13, CYAN, True); add_text(s, "UNAUTHORISED / SCAM", 6.55, 3.18, 2.4, .2, 8, MUTED, True)
    add_text(s, "DAY 61+", 10.75, 2.78, 1.1, .25, 13, RED, True); add_text(s, "AUTOMATIC BLOCK", 10.45, 3.18, 1.7, .2, 8, MUTED, True)
    line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(3.7), Inches(10.95), Inches(.08)); line.fill.solid(); line.fill.fore_color.rgb = CYAN; line.line.fill.background()
    for x, color in [(1.0, CYAN), (3.4, AMBER), (7.15, CYAN), (11.0, RED)]:
        dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(3.55), Inches(.38), Inches(.38)); dot.fill.solid(); dot.fill.fore_color.rgb = color; dot.line.color.rgb = color
    add_box(s, .65, 4.75, 5.75, 1.45, fill=RGBColor(12, 55, 56), line=CYAN); add_text(s, "IN-WINDOW ACH / WIRE", .95, 5.03, 2.7, .2, 9, CYAN, True); add_text(s, "Simulated request raised", .95, 5.38, 2.7, .28, 16, WHITE, True); add_text(s, "IR-ACH-8F41C2  |  No guaranteed recovery", .95, 5.82, 4.8, .2, 9, MUTED, False, "DM Mono")
    add_box(s, 6.9, 4.75, 5.75, 1.45, fill=RGBColor(66, 30, 39), line=RED); add_text(s, "EXPIRED OR INSTANT FINALITY", 7.2, 5.03, 3.5, .2, 9, RED, True); add_text(s, "No-remedy / manual review", 7.2, 5.38, 3.5, .28, 16, WHITE, True); add_text(s, "No late automatic request", 7.2, 5.82, 3.5, .2, 9, MUTED, False, "DM Mono")


def slide_5(prs):
    s = add_base(prs, 5, "Wow factor 01", "Time-travel the rulebook", "A live SLA tester turns policy behavior into something an operator can see and challenge.")
    add_box(s, .65, 2.15, 12, 1.65, fill=PANEL, line=CYAN); add_text(s, "SIMULATE TRANSACTION AGE  /  SLA TESTER", .95, 2.43, 3.6, .2, 9, CYAN, True); add_text(s, "DAY 47", 5.85, 2.42, 1.2, .3, 19, AMBER, True, align=PP_ALIGN.CENTER); add_text(s, "APPROACHING DEADLINE", 5.25, 2.85, 2.5, .2, 9, AMBER, True, align=PP_ALIGN.CENTER)
    slider = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(3.4), Inches(10.9), Inches(.1)); slider.fill.solid(); slider.fill.fore_color.rgb = RGBColor(60, 78, 91); slider.line.fill.background()
    for x, color in [(1.0, CYAN), (8.2, AMBER), (11.4, RED)]:
        dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(3.23), Inches(.45), Inches(.45)); dot.fill.solid(); dot.fill.fore_color.rgb = color; dot.line.color.rgb = color
    add_text(s, "10 days  /  SAFE", 1.0, 3.63, 1.6, .2, 8, CYAN, True); add_text(s, "60-day threshold", 7.8, 3.63, 1.7, .2, 8, AMBER, True); add_text(s, "70 days  /  NO REMEDY", 10.15, 3.63, 1.75, .2, 8, RED, True)
    for i, (title, text, color) in enumerate([("GREEN", "Automatic path", CYAN), ("AMBER", "Analyst attention", AMBER), ("RED", "No-remedy active", RED)]):
        x = .65 + i * 4.1; add_box(s, x, 4.45, 3.6, 1.55, fill=PANEL, line=color); add_text(s, title, x + .25, 4.72, 1.2, .2, 10, color, True); add_text(s, text, x + .25, 5.15, 2.6, .3, 16, WHITE, True); add_text(s, "Same case. Different policy outcome.", x + .25, 5.62, 2.9, .2, 9, MUTED)


def slide_6(prs):
    s = add_base(prs, 6, "Wow factor 02", "Agentic Smart Audit: context before action", "Three specialist checks prepare the operator; none can bypass deterministic policy or human approval.")
    add_box(s, .65, 2.1, 7.15, 4.45, fill=RGBColor(28, 27, 59), line=LILAC); add_text(s, "AGENTIC SMART AUDIT VERDICT", .95, 2.4, 3.8, .2, 9, LILAC, True)
    nodes = [("MATCH", "94% evidence", CYAN), ("POLICY", "60-day PASS", AMBER), ("RISK", "12% LOW", LILAC)]
    for i, (name, detail, color) in enumerate(nodes):
        x = .98 + i * 2.15; add_box(s, x, 2.95, 1.75, .85, fill=RGBColor(39, 39, 76), line=color); add_text(s, name, x + .15, 3.13, 1.45, .18, 9, color, True, align=PP_ALIGN.CENTER); add_text(s, detail, x + .15, 3.48, 1.45, .16, 9, WHITE, True, align=PP_ALIGN.CENTER)
    add_text(s, "BEHAVIORAL FLAG", .98, 4.35, 1.8, .2, 8, AMBER, True); add_text(s, "Customer has historical high reliability. 0 past buyer's remorse claims in 12 months.", .98, 4.7, 5.9, .4, 12, WHITE, True)
    add_text(s, "RECOMMENDATION", .98, 5.35, 1.8, .2, 8, LILAC, True); add_text(s, "Safe to approve simulated interbank recovery request.", .98, 5.7, 5.9, .3, 14, WHITE, True)
    add_box(s, 8.15, 2.1, 4.5, 4.45, fill=PANEL, line=CYAN); add_text(s, "HUMAN APPROVAL REQUIRED", 8.48, 2.48, 3.6, .25, 10, CYAN, True); add_text(s, "AI prepares the case.\nThe operator owns the action.", 8.48, 3.15, 3.5, .8, 22, WHITE, True); add_text(s, "Pre-audit context, not autonomous submission.", 8.48, 5.35, 3.3, .4, 11, MUTED)


def slide_7(prs):
    s = add_base(prs, 7, "Definition of done", "Faster decisions. Fewer unsafe submissions. Better explanations.", "UC-02 measures operational quality, not just chatbot response time.")
    cards = [("SPEED", "Extract facts\nRank candidates", CYAN), ("CONTROL", "Rail + deadline\ngates", AMBER), ("QUALITY", "Abstain instead\nof guessing", LILAC), ("TRUST", "Audit + redaction\n+ honest outcomes", CORAL)]
    for i, (title, text, color) in enumerate(cards):
        x = .65 + i * 3.05; add_box(s, x, 2.2, 2.7, 1.55, fill=PANEL, line=color); add_text(s, title, x + .2, 2.48, 1.4, .2, 9, color, True); add_text(s, text, x + .2, 2.9, 2.2, .5, 15, WHITE, True)
    add_box(s, .65, 4.2, 7.1, 2.1, fill=PANEL, line=LINE); add_text(s, "OPERATIONAL SCORECARD", .95, 4.48, 2.5, .2, 9, CYAN, True)
    metrics = [("Matched cases", 72, CYAN), ("Clarification / abstention", 33, AMBER), ("Human classification overrides", 17, LILAC)]
    for i, (label, value, color) in enumerate(metrics):
        y = 4.88 + i * .43; add_text(s, label, .95, y, 2.4, .18, 9, MUTED); bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(3.2), Inches(y + .04), Inches(3.5), Inches(.12)); bar.fill.solid(); bar.fill.fore_color.rgb = RGBColor(35, 58, 70); bar.line.fill.background(); fill = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(3.2), Inches(y + .04), Inches(3.5 * value / 100), Inches(.12)); fill.fill.solid(); fill.fill.fore_color.rgb = color; fill.line.fill.background(); add_text(s, f"{value}%", 6.9, y - .03, .5, .2, 10, color, True)
    add_box(s, 8.1, 4.2, 4.55, 2.1, fill=RGBColor(12, 55, 56), line=CYAN); add_text(s, "THE UC-02 PROMISE", 8.42, 4.5, 2.5, .2, 9, CYAN, True); add_text(s, "Probabilistic understanding\ninside a deterministic\ncompliance boundary.", 8.42, 4.95, 3.3, .9, 20, WHITE, True); add_text(s, "Human accountability stays in the loop.", 8.42, 6.0, 3.4, .2, 9, MUTED)


def build():
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    for builder in (slide_1, slide_2, slide_3, slide_4, slide_5, slide_6, slide_7): builder(prs)
    prs.core_properties.title = "UC-02 Core Payment Exceptions & Automated Dispute Portal"
    prs.core_properties.subject = "FinTech product and technical demo pitch"
    prs.core_properties.author = "Clearline"
    prs.save(OUTPUT)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    build()