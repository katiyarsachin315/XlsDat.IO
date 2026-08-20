import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st

# ────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CSV/Excel → DAT Converter",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# NOTE: This is a single self-contained file — no .streamlit/config.toml needed.
# Theming (dark/light) is handled entirely below via injected CSS with
# !important overrides, so it works regardless of Streamlit's own default theme.

# ────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ────────────────────────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "df" not in st.session_state:
    st.session_state.df = None
if "original_headers" not in st.session_state:
    st.session_state.original_headers = []
if "cleaned_headers" not in st.session_state:
    st.session_state.cleaned_headers = []
if "file_name" not in st.session_state:
    st.session_state.file_name = None
if "dat_bytes" not in st.session_state:
    st.session_state.dat_bytes = None


def clean_header(text: str) -> str:
    """Remove whitespace and special characters (e.g. $ & # @ etc.) from a header,
    keeping only letters, numbers, and underscores."""
    cleaned = re.sub(r"\s+", "", str(text).strip())
    cleaned = re.sub(r"[^0-9a-zA-Z_]", "", cleaned)
    return cleaned


# ────────────────────────────────────────────────────────────────────────────
# THEME / CSS
# ────────────────────────────────────────────────────────────────────────────
DARK = {
    "bg": "#0b0f14",
    "bg_grad": "linear-gradient(160deg, #0b0f14 0%, #10151d 45%, #0b0f14 100%)",
    "card": "#131a23",
    "card_border": "#232c38",
    "text": "#e8edf3",
    "muted": "#8a96a3",
    "accent": "#6ee7c8",
    "accent2": "#7aa2ff",
    "input_bg": "#0f151d",
    "input_border": "#2a3441",
    "shadow": "0 8px 30px rgba(0,0,0,0.45)",
}
LIGHT = {
    "bg": "#f4f6f9",
    "bg_grad": "linear-gradient(160deg, #f7f9fc 0%, #eef1f6 45%, #f7f9fc 100%)",
    "card": "#ffffff",
    "card_border": "#e3e7ee",
    "text": "#131a23",
    "muted": "#5b6472",
    "accent": "#0f9d76",
    "accent2": "#3b5bdb",
    "input_bg": "#ffffff",
    "input_border": "#d7dce4",
    "shadow": "0 8px 24px rgba(20,30,50,0.08)",
}

T = DARK if st.session_state.theme == "dark" else LIGHT

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"]  {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    .stApp {{
        background: {T['bg_grad']} !important;
        color: {T['text']} !important;
    }}

    /* ── Global text color fix (labels, markdown, widget captions) ───────── */
    .stApp, .stApp p, .stApp span, .stApp label, .stApp li,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stWidgetLabel"] p,
    [data-testid="stCaptionContainer"] {{
        color: {T['text']} !important;
    }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
        color: {T['text']} !important;
    }}

    section[data-testid="stSidebar"] {{
        background: {T['card']} !important;
        border-right: 1px solid {T['card_border']};
    }}
    section[data-testid="stSidebar"] * {{
        color: {T['text']} !important;
    }}

    /* Hide default streamlit chrome */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{background: transparent;}}

    .hero {{
        padding: 28px 32px;
        border-radius: 18px;
        background: linear-gradient(135deg, {T['accent']}22, {T['accent2']}22);
        border: 1px solid {T['card_border']};
        margin-bottom: 28px;
        box-shadow: {T['shadow']};
    }}
    .hero h1 {{
        margin: 0;
        font-size: 30px;
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, {T['accent']}, {T['accent2']});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .hero p {{
        margin: 6px 0 0 0;
        color: {T['muted']} !important;
        font-size: 15px;
    }}

    .card {{
        background: {T['card']} !important;
        border: 1px solid {T['card_border']};
        border-radius: 16px;
        padding: 20px 22px;
        margin-bottom: 20px;
        box-shadow: {T['shadow']};
    }}

    .card h3 {{
        margin-top: 0;
        font-size: 17px;
        font-weight: 700;
        color: {T['text']} !important;
    }}

    .step-badge {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 24px; height: 24px;
        border-radius: 50%;
        background: linear-gradient(135deg, {T['accent']}, {T['accent2']});
        color: #0b0f14 !important;
        font-weight: 800;
        font-size: 12px;
        margin-right: 8px;
    }}

    /* ── Text inputs ───────────────────────────────────────────────────── */
    div[data-testid="stTextInput"] input {{
        background-color: {T['input_bg']} !important;
        border: 1px solid {T['input_border']} !important;
        color: {T['text']} !important;
        border-radius: 10px !important;
        padding: 8px 12px !important;
    }}
    div[data-testid="stTextInput"] input:focus {{
        border-color: {T['accent']} !important;
        box-shadow: 0 0 0 2px {T['accent']}33 !important;
    }}
    div[data-testid="stTextInput"] label p {{
        color: {T['muted']} !important;
        font-size: 12.5px !important;
        font-weight: 600 !important;
    }}

    /* ── Selectbox / dropdown ─────────────────────────────────────────── */
    div[data-testid="stSelectbox"] label p {{
        color: {T['muted']} !important;
        font-size: 12.5px !important;
        font-weight: 600 !important;
    }}
    /* Nuke every element inside the select control so no nested node can
       stay on its default white background regardless of DOM structure. */
    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stSelectbox"] div[data-baseweb="select"] * {{
        background-color: {T['input_bg']} !important;
        background: {T['input_bg']} !important;
        color: {T['text']} !important;
        -webkit-text-fill-color: {T['text']} !important;
        border-color: {T['input_border']} !important;
        fill: {T['text']} !important;
        stroke: {T['text']} !important;
    }}
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {{
        border-radius: 10px !important;
        border: 1px solid {T['input_border']} !important;
    }}
    /* The open dropdown list is portaled to <body>, so it's outside
       stSelectbox — target it separately and nuke it the same way. */
    ul[data-testid="stSelectboxVirtualDropdown"],
    ul[data-testid="stSelectboxVirtualDropdown"] *,
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] *,
    div[data-baseweb="menu"],
    div[data-baseweb="menu"] * {{
        background-color: {T['card']} !important;
        background: {T['card']} !important;
        color: {T['text']} !important;
        -webkit-text-fill-color: {T['text']} !important;
    }}
    ul[data-testid="stSelectboxVirtualDropdown"] li:hover,
    div[data-baseweb="menu"] li:hover {{
        background-color: {T['input_bg']} !important;
        background: {T['input_bg']} !important;
    }}

    /* ── Radio / checkbox ──────────────────────────────────────────────── */
    div[data-testid="stRadio"] label span,
    div[data-testid="stCheckbox"] label span {{
        color: {T['text']} !important;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label {{
        background: {T['input_bg']};
        border: 1px solid {T['input_border']};
        border-radius: 10px;
        padding: 4px 12px;
        margin-right: 6px;
    }}

    /* ── Buttons ───────────────────────────────────────────────────────── */
    .stButton > button, .stDownloadButton > button {{
        background: linear-gradient(135deg, {T['accent']}, {T['accent2']}) !important;
        color: #0b0f14 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 22px !important;
        font-weight: 700 !important;
        font-size: 14.5px !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        box-shadow: {T['shadow']};
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 10px 26px {T['accent']}44;
        color: #0b0f14 !important;
    }}
    .stButton > button p, .stDownloadButton > button p {{
        color: #0b0f14 !important;
        font-weight: 700 !important;
    }}

    /* ── File uploader ─────────────────────────────────────────────────── */
    /* Nuke every element inside the uploader too, for the same reason. */
    div[data-testid="stFileUploader"],
    div[data-testid="stFileUploader"] section,
    div[data-testid="stFileUploader"] section *,
    div[data-testid="stFileUploaderDropzone"],
    div[data-testid="stFileUploaderDropzone"] * {{
        background-color: {T['input_bg']} !important;
        background: {T['input_bg']} !important;
        color: {T['text']} !important;
        -webkit-text-fill-color: {T['text']} !important;
    }}
    div[data-testid="stFileUploader"] section {{
        border: 1.5px dashed {T['input_border']} !important;
        border-radius: 14px !important;
    }}
    div[data-testid="stFileUploader"] small {{
        color: {T['muted']} !important;
        -webkit-text-fill-color: {T['muted']} !important;
    }}
    div[data-testid="stFileUploader"] button,
    div[data-testid="stFileUploaderDropzone"] button {{
        background: {T['card']} !important;
        color: {T['text']} !important;
        border: 1px solid {T['input_border']} !important;
    }}
    div[data-testid="stFileUploaderFile"],
    div[data-testid="stFileUploaderFile"] * {{
        background: {T['input_bg']} !important;
        color: {T['text']} !important;
        border-radius: 8px;
    }}

    /* ── Alerts (success / error / info) ─────────────────────────────────*/
    div[data-testid="stAlert"] p {{
        color: {T['text']} !important;
    }}

    .pill {{
        display: inline-block;
        padding: 3px 12px;
        border-radius: 999px;
        background: {T['accent']}22;
        color: {T['accent']} !important;
        font-size: 12px;
        font-weight: 700;
        margin-left: 8px;
    }}

    .header-chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: {T['input_bg']};
        border: 1px solid {T['input_border']};
        border-radius: 10px;
        padding: 6px 12px;
        margin: 4px 6px 4px 0;
        font-size: 13px;
        color: {T['text']} !important;
    }}
    .header-chip .idx {{
        color: {T['accent']};
        font-weight: 700;
        font-size: 11px;
    }}

    hr {{ border-color: {T['card_border']}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    theme_choice = st.radio(
        "Theme",
        ["Dark", "Light"],
        index=0 if st.session_state.theme == "dark" else 1,
        horizontal=True,
    )
    new_theme = "dark" if theme_choice == "Dark" else "light"
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    st.markdown("---")
    st.markdown("### 📤 Upload File")
    uploaded_file = st.file_uploader(
        "CSV or Excel file", type=["csv", "xlsx", "xls"], label_visibility="collapsed"
    )

    st.markdown("---")
    delimiter_label = st.radio(
        "Output delimiter",
        ["Tab (\\t)", "Comma (,)", "Pipe (|)", "Semicolon (;)"],
        index=0,
    )
    delim_map = {"Tab (\\t)": "\t", "Comma (,)": ",", "Pipe (|)": "|", "Semicolon (;)": ";"}
    output_delim = delim_map[delimiter_label]

    include_index = st.checkbox("Include row index", value=False)

# ────────────────────────────────────────────────────────────────────────────
# HERO
# ────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
        <h1>CSV / Excel → .DAT Converter</h1>
        <p>Upload a file, auto-clean the headers, tweak them if needed, and generate a delimited .dat file — all in a few clicks.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ────────────────────────────────────────────────────────────────────────────
# LOAD FILE
# ────────────────────────────────────────────────────────────────────────────
if uploaded_file is not None:
    if uploaded_file.name != st.session_state.file_name:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
            else:
                df = pd.read_excel(uploaded_file, dtype=str)
                df = df.fillna("")
        except Exception as e:
            st.error(f"Could not read the file: {e}")
            df = None

        if df is not None:
            st.session_state.df = df
            st.session_state.original_headers = list(df.columns)
            st.session_state.cleaned_headers = [clean_header(c) for c in df.columns]
            st.session_state.file_name = uploaded_file.name
            st.session_state.dat_bytes = None

if st.session_state.df is not None:
    df = st.session_state.df

    # ── Step 1: file summary + original headers ──────────────────────
    chips = "".join(
        f'<span class="header-chip"><span class="idx">{i+1}</span>{h}</span>'
        for i, h in enumerate(st.session_state.original_headers)
    )
    st.markdown(
        f"""<div class="card">
        <h3><span class="step-badge">1</span>File loaded
        <span class="pill">{df.shape[0]} rows × {df.shape[1]} cols</span></h3>
        <div style="margin-top:10px;">{chips}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Step 2: editable headers ────────────────────────────────────
    st.markdown(
        """<div class="card"><h3><span class="step-badge">2</span>Review &amp; edit headers
        <span class="pill">spaces &amp; special characters auto-removed</span></h3></div>""",
        unsafe_allow_html=True,
    )

    n_cols = 3
    cols_ui = st.columns(n_cols)
    edited_headers = []
    for i, (orig, cleaned) in enumerate(
        zip(st.session_state.original_headers, st.session_state.cleaned_headers)
    ):
        col = cols_ui[i % n_cols]
        with col:
            label = orig if orig == cleaned else f"{orig}  →  cleaned"
            val = st.text_input(label, value=cleaned, key=f"hdr_{i}")
            edited_headers.append(val)

    # ── Step 3: generate ─────────────────────────────────────────────
    st.markdown(
        """<div class="card"><h3><span class="step-badge">3</span>Generate .dat file</h3></div>""",
        unsafe_allow_html=True,
    )

    dup_check = [h for h in edited_headers if edited_headers.count(h) > 1]
    empty_check = any(h.strip() == "" for h in edited_headers)

    if dup_check:
        st.error(f"Duplicate header names found: {sorted(set(dup_check))}. Please make them unique.")
    elif empty_check:
        st.error("One or more headers are empty. Please fill them in.")
    else:
        gen_col, dl_col = st.columns([1, 1])
        with gen_col:
            generate = st.button("⚡ Generate .dat File", use_container_width=True)

        if generate:
            out_df = df.copy()
            out_df.columns = edited_headers

            buffer = io.StringIO()
            out_df.to_csv(buffer, sep=output_delim, index=include_index)
            st.session_state.dat_bytes = buffer.getvalue().encode("utf-8")
            st.success("✅ .dat file generated successfully!")

        if st.session_state.dat_bytes is not None:
            base_name = (
                st.session_state.file_name.rsplit(".", 1)[0]
                if st.session_state.file_name
                else "output"
            )
            out_name = f"{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dat"
            with dl_col:
                st.download_button(
                    "⬇️ Download .dat File",
                    data=st.session_state.dat_bytes,
                    file_name=out_name,
                    mime="text/plain",
                    use_container_width=True,
                )
else:
    st.markdown(
        """<div class="card" style="text-align:center; padding: 60px 20px;">
        <h3>👋 Upload a CSV or Excel file from the sidebar to get started</h3>
        </div>""",
        unsafe_allow_html=True,
    )