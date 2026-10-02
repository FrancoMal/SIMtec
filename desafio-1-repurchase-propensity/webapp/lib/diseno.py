"""Sistema visual compartido de la aplicación SIMtec."""
import streamlit as st

NAVY = "#00095B"
BLUE = "#1700F3"
MUTED = "#58647C"
SURFACE = "#F4F6FA"
BORDER = "#DCE2EC"
PALETA = [BLUE, NAVY, "#687CC3", "#A6B3D8", "#DCE2EC"]


def aplicar_estilo():
    st.markdown("""
    <style>
      :root {--simtec-navy:#00095B; --simtec-blue:#1700F3; --simtec-muted:#58647C;
             --simtec-content-width:1440px; --simtec-gutter:2.8rem; --simtec-header-height:3.75rem;}
      html, body, [data-testid="stApp"] {font-family:"Segoe UI",Arial,sans-serif;}
      .stApp {background:#FFFFFF; color:#00095B;}
      /* Reservar la altura de la barra superior para que no tape el selector de datos. */
      .block-container {max-width:var(--simtec-content-width);
                        padding:calc(var(--simtec-header-height) + 1.5rem) var(--simtec-gutter) 4rem;}
      [data-testid="stHeader"] {background:#FFFFFF; border-bottom:1px solid #DCE2EC;}
      [data-testid="stToolbar"] .rc-overflow {max-width:var(--simtec-content-width); margin-inline:auto;
                                            padding-inline:calc(var(--simtec-gutter) - .5rem);}
      h1,h2,h3 {font-family:"Segoe UI",Arial,sans-serif !important; color:#00095B; letter-spacing:-.025em;}
      h1 {font-size:2rem !important; font-weight:650 !important; padding-bottom:.4rem !important;}
      h2 {font-size:1.4rem !important; font-weight:600 !important;}
      h3 {font-size:1.12rem !important; font-weight:600 !important;}
      [data-testid="stCaptionContainer"] {color:#58647C;}
      .marca {font-size:1.7rem; font-weight:700; letter-spacing:-.05em; line-height:1.2;}
      .marca span {display:block; font-size:.86rem; font-weight:400; color:#58647C; letter-spacing:0; margin-top:.3rem;}
      [data-testid="stMetric"] {border-top:2px solid #DCE2EC; padding:.9rem 0 .7rem;}
      [data-testid="stMetricValue"] {font-size:1.9rem; color:#00095B; font-weight:600;}
      [data-testid="stMetricLabel"] {color:#58647C; font-size:.85rem;}
      [data-testid="stBaseButton-primary"] {background:#00095B; border-color:#00095B;}
      [data-testid="stBaseButton-primary"]:hover {background:#1700F3; border-color:#1700F3;}
      [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {border-color:#DCE2EC;}
      [data-testid="stFileUploaderDropzone"] {background:#F4F6FA; border:1px dashed #A6B3D8;}
      [data-testid="stDataFrame"] {border:1px solid #DCE2EC; border-radius:6px; overflow:hidden;}
      [data-baseweb="tab-list"] {gap:1.2rem; border-bottom:1px solid #DCE2EC;}
      [data-baseweb="tab"] {font-weight:500;}
      hr {border-color:#DCE2EC !important; margin:1rem 0 1.5rem !important;}
      button:focus-visible, a:focus-visible, input:focus-visible {outline:2px solid #1700F3 !important; outline-offset:3px;}
      @media (max-width:760px) {
        :root {--simtec-gutter:1rem;}
        .block-container {padding-top:calc(var(--simtec-header-height) + 1rem); padding-bottom:3rem;}
        h1 {font-size:1.6rem !important;}
        [data-testid="stMetricValue"] {font-size:1.55rem;}
      }
      @media (prefers-reduced-motion:reduce) {*, *::before, *::after {animation:none !important; transition:none !important;}}
    </style>
    """, unsafe_allow_html=True)


def encabezado(titulo: str, descripcion: str = ""):
    st.title(titulo)
    if descripcion:
        st.write(descripcion)


def estilo_grafico(fig):
    margenes = {"l": 12, "r": 16, "t": 35, "b": 20, **fig.layout.margin.to_plotly_json()}
    fig.update_layout(template="plotly_white", colorway=PALETA,
                      font=dict(family="Segoe UI, Arial, sans-serif", color=NAVY, size=13),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=margenes,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                      hoverlabel=dict(bgcolor="white", font_size=13))
    fig.update_xaxes(gridcolor=SURFACE, zerolinecolor=BORDER, automargin=True)
    fig.update_yaxes(gridcolor=SURFACE, zerolinecolor=BORDER, automargin=True)
    return fig
