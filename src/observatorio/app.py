"""Observatorio da Educacao — painel Streamlit.

Duas bases de dados publicas:
- Ideb municipal (INEP), com recorte nacional;
- IDESP e Saresp (Seduc-SP), para a rede estadual paulista.
"""

from __future__ import annotations

import streamlit as st

from observatorio import ideb_app, idesp_app
from observatorio.ui import CUSTOM_CSS

st.set_page_config(
    page_title="Observatório da Educação",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASES = ["Ideb — Brasil", "IDESP — São Paulo"]


def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    base = st.sidebar.radio("Base de dados", BASES, index=0)
    st.sidebar.divider()

    if base == BASES[0]:
        ideb_app.render()
    else:
        idesp_app.render()

    st.sidebar.divider()
    st.sidebar.caption(
        "Projeto de análise de dados públicos da educação. "
        "Código aberto no [GitHub](https://github.com/henriquesakita/observatorio-educacao) · "
        "[LinkedIn](https://www.linkedin.com/in/henrique-sakita/)."
    )


if __name__ == "__main__":
    main()
