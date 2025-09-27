from pathlib import Path
from PIL import Image
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
from denario import Denario, Journal
from denario import models

from utils import show_markdown_file, create_zip_in_memory, stream_to_streamlit

#--- 
# Components
#---

def description_comp(den: Denario) -> None:

    st.header("Input prompt")

    # Load current data description if it exists
    current_description = ""
    try:
        with open(den.project_dir + "/input_files/data_description.md", 'r', encoding='utf-8') as f:
            current_description = f.read()
    except FileNotFoundError:
        pass

    data_descr = st.text_area(
        "Describe the data and tools to be used in the project. You may also include information about the computing resources required.",
        placeholder="E.g. Analyze the experimental data stored in /path/to/data.csv using sklearn and pandas. This data includes time-series measurements from a particle detector.",
        value=current_description,
        key="data_descr",
        height=100
    )

    uploaded_file = st.file_uploader("Alternatively, upload a file with the data description in markdown format.", accept_multiple_files=False)

    if uploaded_file:
        content = uploaded_file.read().decode("utf-8")
        den.set_data_description(content)   

    if data_descr:

        den.set_data_description(data_descr)

    # Add option to enhance data description
    with st.expander("Enhance Data Description Options"):
        st.caption("Use this option if the description contains arxiv urls.")
        
        model_keys = list(models.keys())
        
        # Get default model indices
        default_summarizer_index = model_keys.index("gpt-4.1") if "gpt-4.1" in model_keys else 0
        default_formatter_index = model_keys.index("o3-mini") if "o3-mini" in model_keys else 0
        
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Summarizer Model: Used to summarize downloaded papers")
            summarizer_model = st.selectbox(
                "Summarizer Model",
                model_keys,
                index=default_summarizer_index,
                key="enhance_summarizer_model"
            )
        with col2:
            st.caption("Summarizer Response Formatter Model: Used to format summarizer responses")
            formatter_model = st.selectbox(
                "Summarizer Response Formatter Model",
                model_keys,
                index=default_formatter_index,
                key="enhance_formatter_model"
            )
        
        enhance_button = st.button("Enhance Data Description", type="secondary", key="enhance_data_desc")

    if enhance_button:
        # Check if data description exists before attempting enhancement
        try:
            with open(den.project_dir + "/input_files/data_description.md", 'r') as f:
                current_description = f.read()
            if not current_description.strip():
                st.warning("No data description found. Please enter a data description above before enhancing it.")
                return
        except FileNotFoundError:
            st.warning("No data description found. Please enter a data description above before enhancing it.")
            return
        
        with st.spinner("Enhancing data description..."):
            try:
                # Try with model parameters first
                try:
                    den.enhance_data_description(
                        summarizer_model=summarizer_model,
                        summarizer_response_formatter_model=formatter_model
                    )
                except TypeError as e:
                    if "unexpected keyword argument" in str(e):
                        # Fallback to method without model parameters (older version)
                        st.warning("Using enhanced data description without model selection (please restart the app to enable model selection)")
                        den.enhance_data_description()
                    else:
                        raise e
                
                st.success("Data description enhanced successfully!")
                # Clear the text area by updating session state
                if "data_descr" in st.session_state:
                    del st.session_state["data_descr"]
                st.rerun()
            except ValueError as e:
                st.error(f"Error: {str(e)}")
            except Exception as e:
                st.error(f"Error enhancing data description: {str(e)}")

    st.markdown("### Current data description")

    try:
        show_markdown_file(den.project_dir+"/input_files/data_description.md",label="data description")
    except FileNotFoundError:
        st.write("Data description not set.")

def idea_comp(den: Denario) -> None:

    st.header("Research idea")
    st.write("Generate a research idea provided the data description.")

    st.write("Choose between a fast generation process or a more involved one using planning and control through [cmbagent](https://github.com/CMBAgents/cmbagent).")

    fast = st.toggle("Fast generation",value=True,key="fast_toggle_idea")

    model_keys = list(models.keys())

    if fast:

        default_fast_idea_index = model_keys.index("gemini-2.0-flash")

        st.caption("Choose a LLM model for the fast generation")
        llm_model = st.selectbox(
            "LLM Model",
            model_keys,
            index=default_fast_idea_index,
            key="llm_model_idea"
        )

    else:

        # Get index of desired default models
        default_idea_maker_index = model_keys.index("gpt-4o")
        default_idea_hater_index = model_keys.index("claude-3.7-sonnet")

        # Add model selection dropdowns
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Idea Maker: Generates and selects the best research ideas based on the data description")
            idea_maker_model = st.selectbox(
                "Idea Maker Model",
                model_keys,
                index=default_idea_maker_index,
                key="idea_maker_model"
            )
        with col2:
            st.caption("Idea Hater: Critiques ideas and proposes recommendations for improvement")
            idea_hater_model = st.selectbox(
                "Idea Hater Model",
                model_keys,
                index=default_idea_hater_index,
                key="idea_hater_model"
            )

    if not fast:
        # Add planner and plan reviewer model selection dropdowns
        col3, col4 = st.columns(2)
        with col3:
            st.caption("Planner: Creates a detailed plan for generating research ideas")
            planner_model = st.selectbox(
                "Planner Model",
                model_keys,
                index=model_keys.index("gpt-4o"),
                key="idea_planner_model"
            )
        with col4:
            st.caption("Plan Reviewer: Reviews and improves the generated plan")
            plan_reviewer_model = st.selectbox(
                "Plan Reviewer Model", 
                model_keys,
                index=model_keys.index("claude-3.7-sonnet"),
                key="idea_plan_reviewer_model"
            )

        col5, col6 = st.columns(2)
        with col5:
            st.caption("Default Orchestration Model")
            default_orchestration_model = st.selectbox(
                "Default Orchestration Model",
                model_keys,
                index=model_keys.index("gpt-4.1"),
                key="idea_orchestration_model"
            )
        with col6:
            st.caption("Default Formatter Model")
            default_formatter_model = st.selectbox(
                "Default Formatter Model",
                model_keys,
                index=model_keys.index("o3-mini"),
                key="idea_formatter_model"
            )
    
    # Initialize session state for tracking operations
    if "idea_running" not in st.session_state:
        st.session_state.idea_running = False
    
    col1, col2 = st.columns([1, 1])
    with col1:
        press_button = st.button("Generate", type="primary", key="get_idea", disabled=st.session_state.idea_running)
    with col2:
        stop_button = st.button("Stop", type="secondary", key="stop_idea", disabled=not st.session_state.idea_running)
    
    # Add custom CSS for red border on stop button
    st.markdown("""
        <style>
        div[data-testid="column"]:nth-of-type(2) button {
            border: 2px solid #ff4444 !important;
            color: #ff4444 !important;
        }
        div[data-testid="column"]:nth-of-type(2) button:hover {
            background-color: #ff4444 !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if press_button and not st.session_state.idea_running:
        st.session_state.idea_running = True
        st.rerun()
    
    if stop_button and st.session_state.idea_running:
        st.session_state.idea_running = False
        st.warning("Operation stopped by user.")
        st.rerun()
    
    if st.session_state.idea_running:
        with st.spinner("Generating research idea...", show_time=True):
            log_box = st.empty()
            
            # Redirect console output to app
            with stream_to_streamlit(log_box):
                try:
                    if fast:
                        den.get_idea_fast(llm=llm_model, verbose=True)
                    else:
                        den.get_idea(idea_maker_model=models[idea_maker_model], idea_hater_model=models[idea_hater_model], 
                                     planner_model=models[planner_model], plan_reviewer_model=models[plan_reviewer_model],
                                     default_orchestration_model=models[default_orchestration_model], default_formatter_model=models[default_formatter_model])
                    
                    if st.session_state.idea_running:  # Only show success if not stopped
                        st.success("Done!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                finally:
                    st.session_state.idea_running = False

    uploaded_file = st.file_uploader("Choose a file with the research idea", accept_multiple_files=False)

    if uploaded_file:
        content = uploaded_file.read().decode("utf-8")
        den.set_idea(content)

    try:
        show_markdown_file(den.project_dir+"/input_files/idea.md", extra_format=True, label="idea")
    except FileNotFoundError:
        st.write("Idea not generated or uploaded.")

def method_comp(den: Denario) -> None:

    st.header("Methods")
    st.write("Generate the methods to be employed in the computation of the results, provided the idea and data description.")

    st.write("Choose between a fast generation process or a more involved one using planning and control through [cmbagent](https://github.com/CMBAgents/cmbagent).")

    fast = st.toggle("Fast generation",value=True,key="fast_toggle_method")

    model_keys = list(models.keys())

    default_fast_method_index = model_keys.index("gemini-2.0-flash")

    if fast:

        st.caption("Choose a LLM model for the fast generation")
        llm_model = st.selectbox(
            "LLM Model",
            model_keys,
            index=default_fast_method_index,
            key="llm_model_method"
        )

    else:

        default_planner_index = model_keys.index("gpt-4o")
        default_plan_reviewer_index = model_keys.index("gpt-4.1")
        default_method_generator_index = model_keys.index("gpt-4o")

        col1, col2 = st.columns(2)
        with col1:
            st.caption("Planner: Creates a detailed plan for generating research methodology")
            planner_model = st.selectbox(
                "Planner Model",
                model_keys,
                index=default_planner_index,
                key="method_planner_model"
            )
        with col2:
            st.caption("Plan Reviewer: Reviews and improves the generated methodology plan")
            plan_reviewer_model = st.selectbox(
                "Plan Reviewer Model", 
                model_keys,
                index=default_plan_reviewer_index,
                key="method_plan_reviewer_model"
            )
        col3, col4 = st.columns(2)
        with col3:
            st.caption("Method Generator: Generates the methodology")
            method_generator_model = st.selectbox(
                "Method Generator Model", 
                model_keys,
                index=default_method_generator_index,
                key="method_generator_model"
            )

        col5, col6 = st.columns(2)
        with col5:
            st.caption("Default Orchestration Model")
            default_orchestration_model = st.selectbox(
                "Default Orchestration Model",
                model_keys,
                index=model_keys.index("gpt-4.1"),
                key="method_orchestration_model"
            )
        with col6:
            st.caption("Default Formatter Model")
            default_formatter_model = st.selectbox(
                "Default Formatter Model",
                model_keys,
                index=model_keys.index("o3-mini"),
                key="method_formatter_model"
            )
    # Initialize session state for tracking operations
    if "method_running" not in st.session_state:
        st.session_state.method_running = False
    
    col1, col2 = st.columns([1, 1])
    with col1:
        press_button = st.button("Generate", type="primary", key="get_method", disabled=st.session_state.method_running)
    with col2:
        stop_button = st.button("Stop", type="secondary", key="stop_method", disabled=not st.session_state.method_running)
    
    # Add custom CSS for red border on stop button
    st.markdown("""
        <style>
        div[data-testid="column"]:nth-of-type(2) button {
            border: 2px solid #ff4444 !important;
            color: #ff4444 !important;
        }
        div[data-testid="column"]:nth-of-type(2) button:hover {
            background-color: #ff4444 !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if press_button and not st.session_state.method_running:
        st.session_state.method_running = True
        st.rerun()
    
    if stop_button and st.session_state.method_running:
        st.session_state.method_running = False
        st.warning("Operation stopped by user.")
        st.rerun()
    
    if st.session_state.method_running:
        with st.spinner("Generating methods...", show_time=True):
            log_box = st.empty()
            
            # Redirect console output to app
            with stream_to_streamlit(log_box):
                try:
                    if fast:
                        den.get_method_fast(llm=llm_model, verbose=True)
                    else:
                        den.get_method(planner_model=planner_model, 
                                       plan_reviewer_model=plan_reviewer_model, 
                                       method_generator_model=method_generator_model,
                                       default_orchestration_model=models[default_orchestration_model], 
                                       default_formatter_model=models[default_formatter_model])
                    
                    if st.session_state.method_running:  # Only show success if not stopped
                        st.success("Done!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                finally:
                    st.session_state.method_running = False

    uploaded_file = st.file_uploader("Choose a file with the research methods", accept_multiple_files=False)

    if uploaded_file:
        content = uploaded_file.read().decode("utf-8")
        den.set_method(content)

    try:
        show_markdown_file(den.project_dir+"/input_files/methods.md",label="methods")
    except FileNotFoundError:
        st.write("Methods not generated or uploaded.")
        
def results_comp(den: Denario) -> None:

    st.header("Analysis")
    st.write("Compute the results, given the methods, idea and data description. This part is done with [cmbagent](https://github.com/CMBAgents/cmbagent).")

    model_keys = list(models.keys())

    # Get index of desired default models
    default_researcher_index = model_keys.index("gemini-2.5-pro")
    default_engineer_index = model_keys.index("gemini-2.5-pro")

    # Add model selection dropdowns
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Engineer: Generates the code to compute the results")
        engineer_model = st.selectbox(
            "Engineer Model",
            model_keys,
            index=default_engineer_index,
            key="engineer_model"
        )
    with col2:
        st.caption("Researcher: processes the results and writes the results report")
        researcher_model = st.selectbox(
            "Researcher Model",
            model_keys,
            index=default_researcher_index,
            key="researcher_model"
        )

    ## add option dropdown for restart at step
    with st.expander("Options for the results generation"):
        restart_at_step = st.number_input("Restart at step", min_value=0, max_value=100, value=0)

        hardware_constraints = st.text_input("Hardware constraints", placeholder="cpu:2, ram:16g, gpu:1")

        default_planner_index = model_keys.index("gpt-4o")
        default_plan_reviewer_index = model_keys.index("claude-3.7-sonnet")

        # add options to control planner, plan_reviewer, researcher and engineer models
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Planner: Creates a detailed plan for generating research results")
            planner_model = st.selectbox(
                "Planner Model",
                model_keys,
                index=default_planner_index,
                key="results_planner_model"
            )
        with col2:
            st.caption("Plan Reviewer: Reviews and improves the proposed plan")
            plan_reviewer_model = st.selectbox(
                "Plan Reviewer Model", 
                model_keys,
                index=default_plan_reviewer_index,
                key="results_plan_reviewer_model"
            )

        col3, col4 = st.columns(2)
        with col3:
            st.caption("Default Orchestration Model")
            default_orchestration_model = st.selectbox(
                "Default Orchestration Model",
                model_keys,
                index=model_keys.index("gpt-4.1"),
                key="results_orchestration_model"
            )
        with col4:
            st.caption("Default Formatter Model")
            default_formatter_model = st.selectbox(
                "Default Formatter Model",
                model_keys,
                index=model_keys.index("o3-mini"),
                key="results_formatter_model"
            )

        # set max n attempts
        max_n_attempts = st.number_input("Max number of code execution attempts", min_value=1, max_value=10, value=6)

        # max n steps
        max_n_steps = st.number_input("Max number of steps", min_value=1, max_value=10, value=6)
    
    # Initialize session state for tracking operations
    if "results_running" not in st.session_state:
        st.session_state.results_running = False
    
    col1, col2 = st.columns([1, 1])
    with col1:
        press_button = st.button("Generate", type="primary", key="get_results", disabled=st.session_state.results_running)
    with col2:
        stop_button = st.button("Stop", type="secondary", key="stop_results", disabled=not st.session_state.results_running)
    
    # Add custom CSS for red border on stop button
    st.markdown("""
        <style>
        div[data-testid="column"]:nth-of-type(2) button {
            border: 2px solid #ff4444 !important;
            color: #ff4444 !important;
        }
        div[data-testid="column"]:nth-of-type(2) button:hover {
            background-color: #ff4444 !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if press_button and not st.session_state.results_running:
        st.session_state.results_running = True
        st.rerun()
    
    if stop_button and st.session_state.results_running:
        st.session_state.results_running = False
        st.warning("Operation stopped by user.")
        st.rerun()
    
    if st.session_state.results_running:
        with st.spinner("Computing results...", show_time=True):
            log_box = st.empty()
            
            # Redirect console output to app
            with stream_to_streamlit(log_box):
                try:
                    den.get_results(engineer_model=models[engineer_model], 
                                    researcher_model=models[researcher_model],
                                    restart_at_step=restart_at_step,
                                    hardware_constraints=hardware_constraints,
                                    planner_model=models[planner_model],
                                    plan_reviewer_model=models[plan_reviewer_model],
                                    max_n_attempts=max_n_attempts,
                                    max_n_steps=max_n_steps,
                                    default_orchestration_model=models[default_orchestration_model],
                                    default_formatter_model=models[default_formatter_model])
                    
                    if st.session_state.results_running:  # Only show success if not stopped
                        st.success("Done!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                finally:
                    st.session_state.results_running = False

    uploaded_files = st.file_uploader("Upload markdown file and/or plots from the results of the research", accept_multiple_files=True)

    if uploaded_files:
        plots = []
        for file in uploaded_files:
            if file.name.endswith(".md"):
                content = file.read().decode("utf-8")
                den.set_results(content)
            else:
                plots.append(Image.open(file))
        den.set_plots(plots)

    plots = list(Path(den.project_dir+"/input_files/plots").glob("*"))

    num_plots = len(list(plots))

    if num_plots>0:
        plots_cols = st.columns(num_plots)

        for i, plot in enumerate(plots):
            with plots_cols[i]:
                st.image(plot, caption=plot.name)

        plots_zip = create_zip_in_memory(den.project_dir+"/input_files/plots")

        st.download_button(
            label="Download plots",
            data=plots_zip,
            file_name="plots.zip",
            mime="application/zip",
            icon=":material/download:",
        )

    else:
        st.write("Plots not generated or uploaded.")

    try:

        codes_zip = create_zip_in_memory(den.project_dir+"/experiment_generation_output")

        st.download_button(
            label="Download codes",
            data=codes_zip,
            file_name="codes.zip",
            mime="application/zip",
            icon=":material/download:",
        )

        show_markdown_file(den.project_dir+"/input_files/results.md",label="results summary")

    except FileNotFoundError:
        st.write("Results not generated or uploaded.")

def paper_comp(den: Denario) -> None:

    st.header("Article")
    st.write("Write the article using the computed results of the research.")

    with st.expander("Options for the paper writing agents"):

        st.caption("Choose a LLM model for the paper generation")
        llm_model = st.selectbox(
            "LLM Model",
            models.keys(),
            index=0,
            key="llm_model_paper"
        )

        selected_journal = st.selectbox(
            "Choose the journal for the latex style:",
            [j.value for j in Journal],
            index=0, key="journal_select")
        
        citations = st.toggle("Add citations",value=True,key="toggle_citations")

        writer = st.text_input(
            "Describe the type of researcher e.g. cosmologist, biologist... Default is 'scientist'.",
            placeholder="scientist",
            key="writer_type",
            value="scientist",
        )

    # Initialize session state for tracking operations
    if "paper_running" not in st.session_state:
        st.session_state.paper_running = False
    
    col1, col2 = st.columns([1, 1])
    with col1:
        press_button = st.button("Generate", type="primary", key="get_paper", disabled=st.session_state.paper_running)
    with col2:
        stop_button = st.button("Stop", type="secondary", key="stop_paper", disabled=not st.session_state.paper_running)
    
    # Add custom CSS for red border on stop button
    st.markdown("""
        <style>
        div[data-testid="column"]:nth-of-type(2) button {
            border: 2px solid #ff4444 !important;
            color: #ff4444 !important;
        }
        div[data-testid="column"]:nth-of-type(2) button:hover {
            background-color: #ff4444 !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if press_button and not st.session_state.paper_running:
        st.session_state.paper_running = True
        st.rerun()
    
    if stop_button and st.session_state.paper_running:
        st.session_state.paper_running = False
        st.warning("Operation stopped by user.")
        st.rerun()
    
    if st.session_state.paper_running:
        with st.spinner("Writing the paper...", show_time=True):
            # log_box = st.empty()

            # Redirect console output to app
            # with stream_to_streamlit(log_box):
            try:
                den.get_paper(journal=selected_journal,
                            llm=llm_model,
                            writer=writer,
                            add_citations=citations)
                
                if st.session_state.paper_running:  # Only show success if not stopped
                    st.success("Done!")
                    st.balloons()
            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                st.session_state.paper_running = False

    try:

        texfile = den.project_dir+"/paper/paper_v4_final.tex"

        # Ensure that the .tex has been created and we can read it
        with open(texfile, "r") as f:
            f.read()

        paper_zip = create_zip_in_memory(den.project_dir+"/paper")

        st.download_button(
            label="Download latex files",
            data=paper_zip,
            file_name="paper.zip",
            mime="application/zip",
            icon=":material/download:",
        )

    except FileNotFoundError:
        st.write("Latex not generated yet.")

    try:

        pdffile = den.project_dir+"/paper/paper_v4_final.pdf"

        with open(pdffile, "rb") as pdf_file:
            PDFbyte = pdf_file.read()

        st.download_button(label="Download pdf",
                    data=PDFbyte,
                    file_name="paper.pdf",
                    mime='application/octet-stream',
                    icon=":material/download:")

        pdf_viewer(pdffile)

    except FileNotFoundError:
        st.write("Pdf not generated yet.")

def check_idea_comp(den: Denario) -> None:
    
    st.header("Literature review")
    st.write("Check if the research idea has been investigated in previous literature. You can choose between two modes based on [Semantic Scholar](https://www.semanticscholar.org/) or [Futurehouse](https://futurehouse.org/).")

    mode = st.selectbox(
        "Choose mode for literature search:",
        options=["semantic_scholar", "futurehouse"],
        index=0,
        key="mode_select_check_idea",
        help="Semantic Scholar: Literature search using Semantic Scholar API\nFuturehouse: Comprehensive search using Futurehouse Owl agent"
    )

    try:
        den.set_idea()
        idea = den.research.idea

        # show current idea
        st.markdown("### Current idea")
        st.write(idea)

        # Initialize session state for tracking operations
        if "literature_running" not in st.session_state:
            st.session_state.literature_running = False
        
        col1, col2 = st.columns([1, 1])
        with col1:
            press_button = st.button("Literature search", type="primary", key="get_literature", disabled=st.session_state.literature_running)
        with col2:
            stop_button = st.button("Stop", type="secondary", key="stop_literature", disabled=not st.session_state.literature_running)
        
        # Add custom CSS for red border on stop button
        st.markdown("""
            <style>
            div[data-testid="column"]:nth-of-type(2) button {
                border: 2px solid #ff4444 !important;
                color: #ff4444 !important;
            }
            div[data-testid="column"]:nth-of-type(2) button:hover {
                background-color: #ff4444 !important;
                color: white !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        if press_button and not st.session_state.literature_running:
            st.session_state.literature_running = True
            st.rerun()
        
        if stop_button and st.session_state.literature_running:
            st.session_state.literature_running = False
            st.warning("Operation stopped by user.")
            st.rerun()
        
        if st.session_state.literature_running:
            with st.spinner("Searching for previous literature...", show_time=True):
                log_box = st.empty()

                # Redirect console output to app
                with stream_to_streamlit(log_box):
                    try:
                        result = den.check_idea(mode=mode, verbose=True)
                        st.write(result)
                        
                        if st.session_state.literature_running:  # Only show success if not stopped
                            st.success("Literature search completed!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                    finally:
                        st.session_state.literature_running = False

    except FileNotFoundError:
        st.write("Need to generate an idea first.")

def referee_comp(den: Denario) -> None:
    
    st.header("Referee report")
    st.write("Review a paper, producing a report providing feedback on the quality of the articled and aspects to be improved.")

    model_keys = list(models.keys())

    default_referee_index = model_keys.index("gemini-2.5-flash")

    st.caption("Choose a LLM model for the referee")
    llm_model = st.selectbox(
        "LLM Model",
        model_keys,
        index=default_referee_index,
        key="llm_model_referee"
    )

    try:

        if "referee_running" not in st.session_state:
            st.session_state.referee_running = False
        
        col1, col2 = st.columns([1, 1])
        with col1:
            press_button = st.button("Review", type="primary", key="start_referee", disabled=st.session_state.referee_running)
        with col2:
            stop_button = st.button("Stop", type="secondary", key="stop_referee", disabled=not st.session_state.referee_running)
        
        # Add custom CSS for red border on stop button
        st.markdown("""
            <style>
            div[data-testid="column"]:nth-of-type(2) button {
                border: 2px solid #ff4444 !important;
                color: #ff4444 !important;
            }
            div[data-testid="column"]:nth-of-type(2) button:hover {
                background-color: #ff4444 !important;
                color: white !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        if press_button and not st.session_state.referee_running:
            st.session_state.referee_running = True
            st.rerun()
        
        if stop_button and st.session_state.referee_running:
            st.session_state.referee_running = False
            st.warning("Operation stopped by user.")
            st.rerun()
        
        if st.session_state.referee_running:
            with st.spinner("Referee reviewing the article...", show_time=True):
                log_box = st.empty()

                # Redirect console output to app
                with stream_to_streamlit(log_box):
                    try:
                        den.referee_fast(llm = llm_model)
                        
                        if st.session_state.referee_running:  # Only show success if not stopped
                            st.success("Referee report completed!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                    finally:
                        st.session_state.referee_running = False

    except FileNotFoundError:
        st.write("Need to generate a paper first.")

    try:
        show_markdown_file(den.project_dir+"/input_files/referee.md",label="referee report")
    except FileNotFoundError:
        st.write("Referee report not created yet.")

def keywords_comp(den: Denario) -> None:

    st.header("Keywords")
    st.write("Generate keywords from your research text.")
    
    input_text = st.text_area(
        "Enter your research text to extract keywords:",
        placeholder="Multi-agent systems (MAS) utilizing multiple Large Language Model agents with Retrieval Augmented Generation and that can execute code locally may become beneficial in cosmological data analysis. Here, we illustrate a first small step towards AI-assisted analyses and a glimpse of the potential of MAS to automate and optimize scientific workflows in Cosmology. The system architecture of our example package, that builds upon the autogen/ag2 framework, can be applied to MAS in any area of quantitative scientific research. The particular task we apply our methods to is the cosmological parameter analysis of the Atacama Cosmology Telescope lensing power spectrum likelihood using Monte Carlo Markov Chains. Our work-in-progress code is open source and available at this https URL.",
        height=200
    )
    
    n_keywords = st.slider("Number of keywords to generate:", min_value=1, max_value=10, value=5)
    
    # Keyword type selection
    kw_type = st.selectbox(
        "Keyword type:",
        options=['unesco', 'aaai', 'aas'],
        index=0,
        help="Choose the keyword taxonomy: UNESCO (general), AAAI (AI/computing), or AAS (astronomy)"
    )
    
    # Initialize session state for tracking operations
    if "keywords_running" not in st.session_state:
        st.session_state.keywords_running = False
    
    col1, col2 = st.columns([1, 1])
    with col1:
        press_button = st.button("Generate Keywords", type="primary", key="get_keywords", disabled=st.session_state.keywords_running)
    with col2:
        stop_button = st.button("Stop", type="secondary", key="stop_keywords", disabled=not st.session_state.keywords_running)
    
    # Add custom CSS for red border on stop button
    st.markdown("""
        <style>
        div[data-testid="column"]:nth-of-type(2) button {
            border: 2px solid #ff4444 !important;
            color: #ff4444 !important;
        }
        div[data-testid="column"]:nth-of-type(2) button:hover {
            background-color: #ff4444 !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if press_button and input_text and not st.session_state.keywords_running:
        st.session_state.keywords_running = True
        st.rerun()
    elif press_button and not input_text:
        st.warning("Please enter some text to generate keywords.")
    
    if stop_button and st.session_state.keywords_running:
        st.session_state.keywords_running = False
        st.warning("Operation stopped by user.")
        st.rerun()
    
    if st.session_state.keywords_running and input_text:
        with st.spinner("Generating keywords..."):
            try:
                den.get_keywords(input_text, n_keywords=n_keywords, kw_type=kw_type)
                
                if st.session_state.keywords_running:  # Only show success if not stopped
                    if hasattr(den.research, 'keywords') and den.research.keywords:
                        st.success("Keywords generated!")
                        st.write("### Generated Keywords")
                        if kw_type == 'aas':
                            # Handle dict format (AAS keywords with URLs)
                            for keyword, url in den.research.keywords.items():
                                st.markdown(f"- [{keyword}]({url})")
                        else:
                            # Handle list format (UNESCO keywords)
                            for keyword in den.research.keywords:
                                st.markdown(f"- {keyword}")
                    else:
                        st.error("No keywords were generated. Please try again with different text.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                st.session_state.keywords_running = False