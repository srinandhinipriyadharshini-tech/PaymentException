from __future__ import annotations

import html
from collections.abc import Mapping, Sequence

import streamlit as st


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
:root {
  --ink:#10242B; --ink-2:#2E4650; --muted:#6E8087; --paper:#F2F4F3; --card:#FFFFFF;
  --line:#D9E0DE; --released:#0F6F5C; --hold:#B9761B; --breached:#A32F2B; --info:#486B78;
}
html, body, [class*="css"], [class*="st-"], .stApp { font-family:'IBM Plex Sans', sans-serif !important; color:var(--ink); line-height:1.6; }
[data-testid="stAppViewContainer"] { background:var(--paper); }
[data-testid="stAppViewContainer"] .stApp, .stApp { background:var(--paper) !important; background-image:none !important; }
[data-testid="stHeader"] { background:transparent; }
footer, #MainMenu { visibility:hidden; }
.block-container, [data-testid="stMainBlockContainer"] { padding-top:2.2rem; padding-bottom:4rem; max-width:1180px; }
[data-testid="stSidebar"] { background:var(--ink); border-right:0; }
[data-testid="stSidebar"] * { color:#E6EDEB; }
[data-testid="stSidebar"] [data-baseweb="select"] * { color:var(--ink) !important; }
h1, h2, h3, button, [data-testid="stMetricValue"], .theme-figure, .theme-ref { font-family:'Archivo', sans-serif !important; }
h1 { font-size:2.05rem; line-height:1.15; letter-spacing:-.021em; }
h2 { font-size:1.35rem; line-height:1.25; }
h3 { font-size:1.05rem; line-height:1.3; }
p, .stCaption, [data-testid="stCaptionContainer"] { max-width:68ch; }
.theme-subtitle, .theme-label, .theme-caption { color:var(--muted); }
.theme-header { border-bottom:1px solid var(--line); padding-bottom:1rem; margin-bottom:1.25rem; }
.theme-header h1 { margin:.1rem 0 .2rem; }
.theme-hero, .theme-note, .theme-queue { background:var(--card); border:1px solid var(--line); border-radius:4px; }
.theme-hero { padding:1.15rem 1.25rem; margin-bottom:1.25rem; }
.theme-queue { padding:1rem 1.15rem; margin-bottom:1.25rem; }
.theme-figures { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; }
.theme-figure { font-size:1.9rem; line-height:1.1; font-variant-numeric:tabular-nums; }
.theme-label { font-size:.75rem; margin-top:.3rem; }
.theme-bar { display:flex; height:8px; margin-top:1rem; overflow:hidden; border-radius:2px; background:var(--line); }
.theme-segment { height:100%; }
.theme-key { display:flex; flex-wrap:wrap; gap:.75rem 1rem; margin-top:.55rem; color:var(--muted); font-size:.75rem; }
.theme-key i { display:inline-block; width:8px; height:8px; margin-right:.25rem; }
.theme-row { display:grid; grid-template-columns:1.15fr 1fr 2fr .8fr 1.2fr; align-items:center; gap:1rem; background:var(--card); border:1px solid var(--line); border-left:3px solid var(--info); border-radius:3px; padding:.8rem 1rem; margin:.45rem 0; }
.theme-row .theme-ref, .theme-row .theme-amount { font-variant-numeric:tabular-nums; }
.theme-status { display:flex; align-items:center; gap:.4rem; color:var(--ink-2); }
.theme-swatch { width:8px; height:8px; background:var(--info); }
.theme-rail { position:relative; display:flex; justify-content:space-between; gap:.75rem; padding-top:1.1rem; margin:1rem 0 1.25rem; }
.theme-rail:before { content:''; position:absolute; left:0; right:0; top:1.35rem; height:3px; background:var(--line); }
.theme-stage { position:relative; z-index:1; flex:1; text-align:center; color:var(--muted); font-size:.75rem; }
.theme-dot { width:12px; height:12px; margin:0 auto .35rem; border:3px solid var(--line); border-radius:50%; background:var(--card); }
.theme-stage.done { color:var(--released); }
.theme-stage.done .theme-dot { border-color:var(--released); background:var(--released); }
.theme-stage.current { color:var(--hold); }
.theme-stage.current .theme-dot { border-color:var(--hold); background:var(--card); }
.theme-note { border-left:3px solid var(--info); padding:.8rem 1rem; margin:.75rem 0; }
.theme-note.hold { border-left-color:var(--hold); }
.theme-note h3 { margin:0 0 .25rem; }
[data-testid="stMetric"] { background:var(--card); border:1px solid var(--line); border-radius:4px; padding:.9rem 1rem; box-shadow:none; }
.stButton > button { font-family:'Archivo', sans-serif; font-weight:500; border-radius:3px; border:1px solid var(--released); background:var(--released); color:white; }
.stButton > button[kind="secondary"] { background:transparent; border-color:var(--line); color:var(--ink); }
.stButton > button:focus-visible, input:focus-visible, textarea:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }
input, textarea, [data-baseweb="select"] > div { border-radius:3px !important; border-color:var(--line) !important; background:var(--card) !important; }
[data-testid="stTabs"] { border-bottom:1px solid var(--line); }
[data-testid="stTabs"] button[aria-selected="true"] { color:var(--released); }
[data-testid="stDataFrame"] { border:1px solid var(--line); }
.hero, .panel, .info-card, .candidate-card, .decision-card, .output-card, .empty-card, .audit-block, .metric, .sandbox { box-shadow:none !important; background-image:none !important; }
.topbar { background:var(--paper) !important; box-shadow:none !important; }
.stButton > button, div.stButton > button, [data-testid="stDownloadButton"] button { border-radius:3px !important; box-shadow:none !important; }
@media (max-width:800px) {
  .theme-figures { grid-template-columns:repeat(2,1fr); }
  .theme-row { grid-template-columns:1fr 1fr; gap:.45rem; }
  .theme-rail { gap:.2rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:0.01ms !important; animation-iteration-count:1 !important; transition-duration:0.01ms !important; scroll-behavior:auto !important; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def setup_page(title: str, icon: str, wide: bool = True) -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout="wide" if wide else "centered", initial_sidebar_state="expanded")
    inject_css()


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<header class="theme-header"><h1>{html.escape(title)}</h1><div class="theme-subtitle">{html.escape(subtitle)}</div></header>',
        unsafe_allow_html=True,
    )


def queue_band(items: int, amount: str, oldest: str, breached: int, aging: Mapping[str, int]) -> None:
    total = sum(max(value, 0) for value in aging.values()) or 1
    colors = ["var(--released)", "var(--info)", "var(--hold)", "var(--breached)"]
    segments = "".join(
        f'<span class="theme-segment" style="width:{max(value, 0) / total * 100:.2f}%;background:{colors[index % len(colors)]}"></span>'
        for index, value in enumerate(aging.values())
    )
    key = "".join(
        f'<span><i style="background:{colors[index % len(colors)]}"></i>{html.escape(str(label))}</span>'
        for index, label in enumerate(aging)
    )
    breach_class = " style=\"color:var(--breached)\"" if breached else ""
    st.markdown(
        f'<section class="theme-queue"><div class="theme-figures">'
        f'<div><div class="theme-figure">{items}</div><div class="theme-label">Waiting</div></div>'
        f'<div><div class="theme-figure">{html.escape(str(amount))}</div><div class="theme-label">Held value</div></div>'
        f'<div><div class="theme-figure">{html.escape(str(oldest))}</div><div class="theme-label">Oldest item</div></div>'
        f'<div><div class="theme-figure"{breach_class}>{breached}</div><div class="theme-label">Past SLA</div></div>'
        f'</div><div class="theme-bar">{segments}</div><div class="theme-key">{key}</div></section>',
        unsafe_allow_html=True,
    )


def exception_row(ref: str, amount: str, reason: str, age: str, status: str) -> None:
    colors = {"released": "var(--released)", "hold": "var(--hold)", "breached": "var(--breached)", "review": "var(--info)", "new": "var(--line)"}
    color = colors.get(status.lower(), "var(--info)")
    st.markdown(
        f'<div class="theme-row" style="border-left-color:{color}"><strong class="theme-ref">{html.escape(ref)}</strong><strong class="theme-amount">{html.escape(amount)}</strong><span>{html.escape(reason)}</span><span>{html.escape(age)}</span><span class="theme-status"><i class="theme-swatch" style="background:{color}"></i>{html.escape(status)}</span></div>',
        unsafe_allow_html=True,
    )


def payment_rail(stages: Sequence[Mapping[str, str]]) -> None:
    rendered = []
    for stage in stages:
        state = stage.get("state", "pending")
        rendered.append(
            f'<div class="theme-stage {html.escape(state)}"><div class="theme-dot"></div><strong>{html.escape(stage.get("label", ""))}</strong><br><span>{html.escape(stage.get("time", ""))}</span></div>'
        )
    st.markdown(f'<div class="theme-rail">{"".join(rendered)}</div>', unsafe_allow_html=True)


def note(title: str, body: str, tone: str = "info") -> None:
    css_tone = "hold" if tone == "hold" else ""
    st.markdown(f'<aside class="theme-note {css_tone}"><h3>{html.escape(title)}</h3><div>{html.escape(body)}</div></aside>', unsafe_allow_html=True)
