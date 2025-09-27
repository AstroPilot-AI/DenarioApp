import os
import argparse
import streamlit as st
from denario import Denario

from constants import PROJECT_DIR, LLMs
from components import description_comp, idea_comp, method_comp, results_comp, paper_comp, keywords_comp, check_idea_comp, referee_comp
from utils import extract_api_keys, get_project_dir, set_api_keys, create_zip_in_memory, delete_old_folders

#---
# Initialize session
#--- 

parser = argparse.ArgumentParser()
parser.add_argument('--deploy',action='store_true',help='Flag to enable special settings for deployment in Huggin Face Spaces')
deploy = parser.parse_args().deploy

if deploy:
    delete_old_folders()
    project_dir = get_project_dir()
else:
    project_dir = PROJECT_DIR

den = Denario(project_dir=project_dir, clear_project_dir=False)

denarioimg = 'https://avatars.githubusercontent.com/u/206478071?s=400&u=b2da27eb19fb77adbc7b12b43da91fbc7309fb6f&v=4'

# streamlit configuration
st.set_page_config(
    page_title="Denario",         # Title of the app (shown in browser tab)
    # page_icon=denarioimg,         # Favicon (icon in browser tab)
    layout="wide",                   # Page layout (options: "centered" or "wide")
    initial_sidebar_state="auto",    # Sidebar behavior
    menu_items=None                  # Custom options for the app menu
)

st.session_state["LLM_API_KEYS"] = {}

st.title('Denario')

st.markdown("""
    <style>
    .log-box {
        background-color: #111827;
        color: #d1d5db;
        font-family: monospace;
        padding: 1em;
        border-radius: 8px;
        max-height: 300px;
        overflow-y: auto;
        border: 1px solid #4b5563;
        white-space: pre-wrap;
        resize: vertical;
        min-height: 100px;
        max-height: 700px;
    }
    </style>
""", unsafe_allow_html=True)


#---
# Sidebar UI
#---

with st.sidebar:

    # st.image(astropilotimg)

    st.header("API keys")
    st.markdown("*Input OpenAI, Anthropic, Gemini and Perplexity API keys below. See [here](https://denario.readthedocs.io/en/latest/apikeys/) for more information.*")

    with st.expander("Set API keys"):

        # If API key doesn't exist, show the input field
        for llm in LLMs:
            api_key = st.text_input(
                f"{llm} API key:",
                type="password",
                key=f"{llm}_api_key_input"
            )
            
            # If the user enters a key, save it and rerun to refresh the interface
            if api_key:
                st.session_state["LLM_API_KEYS"][llm] = api_key
                set_api_keys(den.keys, api_key, llm)
            
            # Check session state
            has_key = st.session_state["LLM_API_KEYS"].get(llm)
            
            # # Display status after the key is saved
            # if has_key:
            #     st.markdown(f"<small style='color:green;'> ✅: {llm} API key set</small>",unsafe_allow_html=True)
            # else:
            #     st.markdown(f"<small style='color:red;'>❌: No {llm} API key</small>", unsafe_allow_html=True)

        st.markdown("""Or just upload a .env file with the following keys and reload the page:
                    
```
OPENAI_API_KEY="..."
ANTHROPIC_API_KEY="..."
GEMINI_API_KEY="..."
PERPLEXITY_API_KEY="..."
```
                    """)
        uploaded_dotenv = st.file_uploader("Upload the .env file", accept_multiple_files=False)

        if uploaded_dotenv:
            keys = extract_api_keys(uploaded_dotenv)

            for key, value in keys.items():
                st.session_state["LLM_API_KEYS"][key] = value
                den.keys[key] = value

    st.header("Upload data")

    uploaded_data = st.file_uploader("Upload the data files", accept_multiple_files=True)

    if uploaded_data:
        os.makedirs(f"{den.project_dir}/data/", exist_ok=True)
        for uploaded_file in uploaded_data:
            with open(f"{den.project_dir}/data/{uploaded_file.name}", "wb") as f:
                f.write(uploaded_file.getbuffer())
        st.success("Files uploaded successfully!")

    st.header("Download project")

    project_zip = create_zip_in_memory(den.project_dir)

    st.download_button(
        label="Download all project files",
        data=project_zip,
        file_name="project.zip",
        mime="application/zip",
        icon=":material/download:",
    )

#---
# Main
#---

st.write("""
        AI agents to assist the development of a scientific research process.
         
        From developing research ideas, developing methods, computing results and writing or reviewing papers.
         """)

# Load Font Awesome CSS
st.markdown(
    """
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    """,
    unsafe_allow_html=True
)

# Icons
st.markdown(
    """
    <div style="text-align: left; margin-top: 0px; margin-bottom: 20px; font-size: 16px;">
        <a href="https://astropilot-ai.github.io/DenarioPaperPage/" target="_blank" style="margin-right: 30px; text-decoration: none; color: inherit;">
            <i class="fa-solid fa-globe"></i> Project Page
        </a>
        <a href="https://denario.readthedocs.io/en/latest/" target="_blank" style="margin-right: 30px; text-decoration: none; color: inherit;">
            <i class="fa-solid fa-book"></i> Documentation
        </a>
        <a href="https://github.com/AstroPilot-AI/Denario" target="_blank" style="margin-right: 30px; text-decoration: none; color: inherit;">
            <i class="fa-brands fa-github"></i> Code
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

# TODO: add above when paper is ready
# <a href="https://your-paper-link.com" target="_blank" style="text-decoration: none; color: inherit;">
#     <i class="fa-solid fa-file-alt"></i> Paper
# </a>

tab_descr, tab_idea, tab_method, tab_restults, tab_paper,  tab_check_idea, tab_referee, tab_keywords,= st.tabs([
    "**Input prompt**", 
    "**Idea**", 
    "**Methods**", 
    "**Analysis**", 
    "**Paper**", 
    "Literature review",
    "Referee report",
    "Keywords"
])

with tab_descr:
    description_comp(den)

with tab_idea:
    idea_comp(den)

with tab_method:
    method_comp(den)

with tab_restults:
    results_comp(den)

with tab_paper:
    paper_comp(den)

with tab_check_idea:
    check_idea_comp(den)

with tab_referee:
    referee_comp(den)

with tab_keywords:
    keywords_comp(den)