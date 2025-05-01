import streamlit as st
import hmac
import PyPDF2
import io
import datetime
import json
import os

# Set page configuration first
st.set_page_config(page_title="Project Management Tool", layout="wide")

# Initialize basic session state before anything else
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if "current_view" not in st.session_state:
        st.session_state.current_view = "AI Assistant"
    if "canvas_text" not in st.session_state:
        st.session_state.canvas_text = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "project_prompts" not in st.session_state:
        st.session_state.project_prompts = {}
    if "documents" not in st.session_state:
        st.session_state.documents = []
    if "logging_out" not in st.session_state:
        st.session_state.logging_out = False

def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials", clear_on_submit=False):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            submit = st.form_submit_button("Log in")
            if submit:
                password_entered()

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        try:
            if st.session_state["username"] in st.secrets["passwords"] and hmac.compare_digest(
                st.session_state["password"],
                st.secrets.passwords[st.session_state["username"]],
            ):
                st.session_state["password_correct"] = True
                if "password" in st.session_state:
                    del st.session_state["password"]  # Don't store the password
                if "username" in st.session_state:
                    del st.session_state["username"]  # Don't store the username
            else:
                st.session_state["password_correct"] = False
        except Exception as e:
            st.error(f"Error checking password: {str(e)}")
            st.session_state["password_correct"] = False

    # Return True if the username + password is validated
    if st.session_state.get("password_correct", False):
        return True

    # Show login page
    st.title("Project Management Tool - Login")
    st.write("Please log in to access the application.")
    login_form()
    
    # Only show the error message if the user attempted to log in (not during logout)
    if "password_correct" in st.session_state and not st.session_state.get("password_correct", True) and not st.session_state.get("logging_out", False):
        st.error("😕 User not known or password incorrect")
    
    # Reset the logging_out flag
    if st.session_state.get("logging_out", False):
        st.session_state["logging_out"] = False
        
    return False

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += f"\n--- Page {page_num + 1} ---\n"
            text += page.extract_text()
    except Exception as e:
        text = f"Error extracting text: {str(e)}"
    return text

def process_pdfs(uploaded_files):
    """Process uploaded PDF files and update the canvas text"""
    if not uploaded_files:
        return
        
    all_pdf_text = ""
    for pdf_file in uploaded_files:
        all_pdf_text += f"\n\n--- Document: {pdf_file.name} ---\n"
        all_pdf_text += extract_text_from_pdf(pdf_file)
    
    # Append the extracted text to the canvas
    if st.session_state.canvas_text:
        st.session_state.canvas_text += "\n\n" + all_pdf_text
    else:
        st.session_state.canvas_text = all_pdf_text

def load_project_prompts():
    """Load default project prompts"""
    return {
        "Project Initiation": [
            "Generate a project charter based on these requirements and constraints",
            "Identify key stakeholders and create a stakeholder analysis matrix",
            "Create a project RACI matrix for the following team members",
            "Define project success criteria and KPIs",
            "Conduct risk assessment based on the following project description",
        ],
        "Project Planning": [
            "Break down this project into a detailed WBS",
            "Create a resource allocation plan based on these constraints",
            "Develop a project timeline with key milestones",
            "Create a budget estimation with contingency for these requirements",
            "Develop a communication plan for these stakeholders",
        ],
        "Project Execution": [
            "Generate a weekly status report template",
            "Develop a change request form and process",
            "Create a team performance tracking system",
            "Generate meeting agenda and minutes template",
            "Develop a dashboard for tracking project KPIs",
        ],
        "Project Monitoring": [
            "Analyze these project metrics and identify potential issues",
            "Calculate earned value metrics based on this progress data",
            "Generate a risk response plan for the following emerging risks",
            "Create a quality control checklist for these deliverables",
            "Develop a corrective action plan for these deviations",
        ],
        "Project Closure": [
            "Create a project closure report template",
            "Generate a lessons learned questionnaire",
            "Develop a knowledge transfer plan template",
            "Create a post-project evaluation framework",
            "Generate a client acceptance document template",
        ]
    }

def init_session_state():
    """Initialize session state variables if not already done"""
    if "project_prompts" not in st.session_state or not st.session_state.project_prompts:
        st.session_state.project_prompts = load_project_prompts()
    
    if "ai_model" not in st.session_state:
        st.session_state.ai_model = st.secrets.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
    
    if 'SYSTEM_PROMPT' not in st.session_state:
        st.session_state.SYSTEM_PROMPT = st.secrets.get("SYSTEM_PROMPT", "You are a project management assistant.")

def create_sidebar():
    """Create the sidebar with navigation and tools"""
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/project-management.png", width=50)
        st.title("Project Hub")
        
        # Navigation (simplified - only Documents and AI Assistant)
        st.subheader("Navigation")
        views = ["Documents", "AI Assistant"]
        for view in views:
            if st.button(view, key=f"nav_{view}"):
                st.session_state.current_view = view
                if "messages" in st.session_state:
                    st.session_state.messages = []  # Clear chat when switching views
                st.rerun()
        
        # Only show project prompts in AI Assistant view
        if st.session_state.current_view == "AI Assistant":
            st.markdown("---")
            st.subheader("Prompt Library")
            
            # Dropdown for prompt categories
            prompt_category = st.selectbox(
                "Select Project Phase",
                list(st.session_state.project_prompts.keys())
            )
            
            # Show prompts for selected category
            if prompt_category:
                for prompt in st.session_state.project_prompts[prompt_category]:
                    if st.button(prompt, key=f"prompt_{prompt}"):
                        if "canvas_text" not in st.session_state:
                            st.session_state.canvas_text = ""
                        
                        # Add selected prompt to canvas
                        if st.session_state.canvas_text:
                            st.session_state.canvas_text += f"\n\n{prompt}"
                        else:
                            st.session_state.canvas_text = prompt
                        st.rerun()
                        
            # Option to add custom prompts
            st.markdown("---")
            with st.expander("Add Custom Prompt"):
                new_category = st.text_input("Category Name", key="new_category")
                new_prompt = st.text_area("Prompt", key="new_prompt")
                if st.button("Add Prompt", key="add_prompt"):
                    if new_category and new_prompt:
                        if new_category not in st.session_state.project_prompts:
                            st.session_state.project_prompts[new_category] = []
                        st.session_state.project_prompts[new_category].append(new_prompt)
                        st.success("Prompt added!")
                        st.rerun()
        
        # Document upload section
        if st.session_state.current_view in ["Documents", "AI Assistant"]:
            st.markdown("---")
            st.subheader("Document Upload")
            st.write("Upload PDF documents to extract text")
            
            # PDF Uploader with callback
            uploaded_pdfs = st.file_uploader(
                "Upload PDFs", 
                type="pdf", 
                accept_multiple_files=True,
                key="pdf_uploader",
                on_change=lambda: process_pdfs(st.session_state.pdf_uploader)
            )
        
        # Clear and logout buttons
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear", key="sidebar_clear"):
                if st.session_state.current_view == "AI Assistant":
                    st.session_state.messages = []
                st.session_state.canvas_text = ""
                st.rerun()
        with col2:
            if st.button("Logout", key="sidebar_logout"):
                st.session_state["logging_out"] = True
                st.session_state["password_correct"] = False
                st.rerun()

def display_documents():
    """Display the documents view for managing project documents"""
    st.title("Document Manager")
    
    # Initialize documents list if not exists
    if "documents" not in st.session_state:
        st.session_state.documents = []
    
    # Document upload form
    st.subheader("Upload Document")
    
    upload_col1, upload_col2 = st.columns([3, 1])
    with upload_col1:
        uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt", "csv", "xlsx"])
    with upload_col2:
        if uploaded_file is not None:
            document_type = st.selectbox(
                "Document Type",
                options=["Requirements", "Plan", "Report", "Meeting Minutes", "Other"]
            )
    
    if uploaded_file is not None:
        st.write("File details:")
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size / 1024:.2f} KB",
            "Type": uploaded_file.type
        }
        
        for key, value in file_details.items():
            st.write(f"**{key}:** {value}")
        
        document_description = st.text_area("Document Description (optional)")
        
        if st.button("Save Document"):
            # Extract text if PDF
            content = ""
            if uploaded_file.type == "application/pdf":
                content = extract_text_from_pdf(uploaded_file)
            
            # Save document
            document = {
                "id": len(st.session_state.documents) + 1,
                "name": uploaded_file.name,
                "type": document_type,
                "description": document_description,
                "upload_date": datetime.datetime.now().isoformat(),
                "content": content,
                "size": uploaded_file.size,
                "file_type": uploaded_file.type
            }
            
            st.session_state.documents.append(document)
            st.success(f"Document '{uploaded_file.name}' saved successfully!")
            st.session_state.canvas_text = content  # Add content to canvas for AI processing
            st.rerun()
    
    # Document library
    st.subheader("Document Library")
    
    if not st.session_state.documents:
        st.info("No documents uploaded yet.")
    else:
        # Filter options
        filter_type = st.multiselect(
            "Filter by Type",
            options=["Requirements", "Plan", "Report", "Meeting Minutes", "Other"],
            default=[]
        )
        
        # Apply filters
        filtered_docs = st.session_state.documents
        if filter_type:
            filtered_docs = [d for d in filtered_docs if d["type"] in filter_type]
        
        # Display documents
        for doc in filtered_docs:
            with st.expander(f"{doc['name']} ({doc['type']})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Type:** {doc['type']}")
                    st.write(f"**Description:** {doc['description'] if doc['description'] else 'No description'}")
                    st.write(f"**Upload Date:** {doc['upload_date'].split('T')[0]}")
                with col2:
                    st.write(f"**Size:** {doc['size'] / 1024:.2f} KB")
                    if doc['content']:
                        if st.button("View Content", key=f"view_{doc['id']}"):
                            st.session_state.canvas_text = doc['content']
                            st.session_state.current_view = "AI Assistant"
                            st.rerun()
                
                # Delete document
                if st.button("Delete Document", key=f"delete_{doc['id']}"):
                    st.session_state.documents.remove(doc)
                    st.success(f"Document '{doc['name']}' deleted successfully!")
                    st.rerun()

def display_ai_assistant():
    """Display the AI Assistant view for project management assistance"""
    st.title("Project Management AI Assistant")
    
    # System prompt for project management focus
    if "ai_system_prompt" not in st.session_state:
        st.session_state.ai_system_prompt = """You are a project management assistant that helps with all aspects of project management. 
        Your role is to provide guidance, templates, and suggestions for each phase of the project lifecycle:
        1. Project Initiation (e.g., creating project charters, stakeholder analysis)
        2. Project Planning (e.g., creating WBS, schedules, risk assessments)
        3. Project Execution (e.g., status reports, team coordination)
        4. Project Monitoring (e.g., performance tracking, issue resolution)
        5. Project Closure (e.g., lessons learned, completion reports)
        
        Provide practical, actionable advice. You can generate templates, plans, and reports based on the information provided.
        Always consider best practices from PMI and PRINCE2 methodologies when applicable.
        """
    
    # Prompt customization
    with st.expander("Customize Assistant", expanded=False):
        ai_system_prompt = st.text_area(
            "System Prompt (specify how the assistant should behave)",
            value=st.session_state.ai_system_prompt,
            height=200
        )
        
        if ai_system_prompt != st.session_state.ai_system_prompt:
            st.session_state.ai_system_prompt = ai_system_prompt
    
    # Text canvas for pasting content
    st.markdown("### Prompt Canvas")
    st.markdown("Enter your prompt or paste project content here:")
    
    # Initialize canvas text in session state if not exists
    if "canvas_text" not in st.session_state:
        st.session_state.canvas_text = ""
    
    # Text area for pasting content
    canvas_input = st.text_area(
        "Enter prompt",
        value=st.session_state.canvas_text,
        height=150,
        key="canvas_area"
    )
    
    # Update session state when text changes
    if canvas_input != st.session_state.canvas_text:
        st.session_state.canvas_text = canvas_input
    
    # Clear canvas button
    if st.button("Clear Canvas"):
        st.session_state.canvas_text = ""
        st.rerun()
    
    # Chat interface
    st.markdown("### Project Management Assistant")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask the Project Management Assistant..."):
        # Combine user's chat input with any text from the canvas
        combined_input = prompt
        
        if st.session_state.canvas_text.strip():
            combined_input = f"{prompt}\n\n**Additional Context:**\n```\n{st.session_state.canvas_text}\n```"
        
        # Add the combined message to history
        st.session_state.messages.append({"role": "user", "content": combined_input})
        
        with st.chat_message("user"):
            st.markdown(combined_input)
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # Try to import and initialize Anthropic client - FIXED VERSION
            try:
                import anthropic
                
                # Get max tokens from secrets or use default
                max_tokens = int(st.secrets.get("MAX_TOKENS", 4096))
                
                # Get model from session state or use default
                model = st.session_state.get("ai_model", "claude-3-haiku-20240307")
                
                # Define output guidelines
                OUTPUT_GUIDELINES = '''
                BLOCK CATEGORY:
                    - Promoting violence, illegal activities, or hate speech
                    - Explicit sexual content
                    - Harmful misinformation or conspiracy theories
                
                    ALLOW CATEGORY:
                    - Most other content is allowed, as long as it is not explicitly disallowed
                '''
                
                # Format system prompt
                system_prompt = st.session_state.ai_system_prompt + f"\n\nPlease adhere to these output guidelines: {OUTPUT_GUIDELINES}"
                
                # Check for newer style API (>= 0.5.0)
                if hasattr(anthropic, "Anthropic"):
                    # Use newer client style - this is the recommended approach
                    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                    
                    # Stream the response
                    full_response = ""
                    with client.messages.stream(
                        max_tokens=max_tokens,
                        system=system_prompt,
                        messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                        model=model,
                    ) as stream:
                        for text in stream.text_stream:
                            full_response += str(text) if text is not None else ""
                            message_placeholder.markdown(full_response + "▌")
                        
                        message_placeholder.markdown(full_response)
                # Check for older style API with Client class
                elif hasattr(anthropic, "Client"):
                    # Use older client style
                    st.info("Using older Anthropic client version. Consider upgrading to the latest version.")
                    
                    # Important fix: Don't pass proxies to the Client constructor
                    client = anthropic.Client(api_key=st.secrets["ANTHROPIC_API_KEY"])
                    
                    # Format prompt for older client
                    prompt_text = f"{anthropic.HUMAN_PROMPT} {combined_input} {anthropic.AI_PROMPT}"
                    
                    # Stream the response
                    full_response = ""
                    response = client.completion_stream(
                        prompt=prompt_text,
                        max_tokens_to_sample=max_tokens,
                        model=model,
                    )
                    
                    for text in response:
                        full_response += text
                        message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                else:
                    # Neither client style is available
                    full_response = "Could not determine the correct Anthropic client type. Please ensure you have a compatible version of the anthropic package installed."
                    message_placeholder.markdown(full_response)
            except ImportError:
                # If anthropic package is not installed
                full_response = "The anthropic package is not installed. Please run 'pip install anthropic' to use the AI Assistant."
                message_placeholder.markdown(full_response)
            except Exception as e:
                # Any other errors
                st.error(f"Error: {str(e)}")
                full_response = "I encountered an error while processing your request. Please check your configuration and try again."
                message_placeholder.markdown(full_response)
            
            # Add the response to chat history
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        # Clear the canvas after sending
        st.session_state.canvas_text = ""

def main():
    """Main function to run the app"""
    # Initialize session state
    init_session_state()
    
    # IMPORTANT: Check password first, before importing any heavy libraries
    if not check_password():
        return
    
    # Create sidebar
    create_sidebar()
    
    # Display the appropriate view (simplified - only Documents and AI Assistant)
    if st.session_state.current_view == "Documents":
        display_documents()
    elif st.session_state.current_view == "AI Assistant":
        display_ai_assistant()
    else:
        # Default to AI Assistant if view is not recognized
        display_ai_assistant()

# Run the main function
if __name__ == "__main__":
    main()
