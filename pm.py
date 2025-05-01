import streamlit as st
import anthropic
import hmac
import PyPDF2
import io
import pandas as pd
import datetime
import json
import os
from streamlit_timeline import timeline

def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in st.secrets[
            "passwords"
        ] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the username or password.
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    
    # Only show the error message if the user attempted to log in (not during logout)
    if "password_correct" in st.session_state and not st.session_state.get("logging_out", False):
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
    
    # Initialize canvas text if not exists
    if "canvas_text" not in st.session_state:
        st.session_state.canvas_text = ""
        
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

def main():
    """Main function to run the app"""
    # Initialize session state
    init_session_state()
    
    # Check password
    if not check_password():
        st.stop()
    
    # Create sidebar
    create_sidebar()
    
    # Display the appropriate view
    if st.session_state.current_view == "Dashboard":
        display_dashboard()
    elif st.session_state.current_view == "Projects":
        display_projects()
    elif st.session_state.current_view == "Documents":
        display_documents()
    elif st.session_state.current_view == "AI Assistant":
        display_ai_assistant()
    else:
        display_dashboard()

def init_session_state():
    """Initialize session state variables"""
    if "current_view" not in st.session_state:
        st.session_state.current_view = "Dashboard"
    
    if "projects" not in st.session_state:
        st.session_state.projects = []
    
    if "canvas_text" not in st.session_state:
        st.session_state.canvas_text = ""
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "project_prompts" not in st.session_state:
        st.session_state.project_prompts = load_project_prompts()
    
    if "current_project" not in st.session_state:
        st.session_state.current_project = None
    
    if "ai_model" not in st.session_state:
        st.session_state.ai_model = st.secrets["ANTHROPIC_MODEL"]
    
    if 'SYSTEM_PROMPT' not in st.session_state:
        st.session_state.SYSTEM_PROMPT = st.secrets["SYSTEM_PROMPT"]
    
    if "documents" not in st.session_state:
        st.session_state.documents = []

def create_sidebar():
    """Create the sidebar with navigation and tools"""
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/project-management.png", width=50)
        st.title("Project Hub")
        
        # Navigation
        st.subheader("Navigation")
        views = ["Dashboard", "Projects", "Documents", "AI Assistant"]
        for view in views:
            if st.button(view, key=f"nav_{view}"):
                st.session_state.current_view = view
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

def display_dashboard():
    """Display the dashboard view with project overview"""
    st.title("Project Management Dashboard")
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Projects", len([p for p in st.session_state.projects if p.get("status") == "Active"]))
    with col2:
        st.metric("Completed Projects", len([p for p in st.session_state.projects if p.get("status") == "Completed"]))
    with col3:
        st.metric("Total Documents", len(st.session_state.get("documents", [])))
    
    # Recent projects
    st.subheader("Recent Projects")
    if not st.session_state.projects:
        st.info("No projects created yet. Go to the Projects tab to create your first project.")
    else:
        recent_projects = sorted(st.session_state.projects, key=lambda x: x.get("last_updated", ""), reverse=True)[:3]
        for project in recent_projects:
            with st.expander(f"{project['name']} ({project['status']})"):
                st.write(f"**Description:** {project['description']}")
                st.write(f"**Start Date:** {project['start_date']}")
                st.write(f"**End Date:** {project['end_date']}")
                progress = project.get("progress", 0)
                st.progress(progress/100)
                st.write(f"Progress: {progress}%")
    
    # Upcoming milestones
    st.subheader("Upcoming Milestones")
    milestones = []
    for project in st.session_state.projects:
        for milestone in project.get("milestones", []):
            milestones.append({
                "project": project["name"],
                "name": milestone["name"],
                "date": milestone["date"],
                "status": milestone["status"]
            })
    
    # Sort and filter upcoming milestones
    today = datetime.date.today().isoformat()
    upcoming = [m for m in milestones if m["date"] >= today and m["status"] != "Completed"]
    upcoming.sort(key=lambda x: x["date"])
    
    if not upcoming:
        st.info("No upcoming milestones.")
    else:
        for milestone in upcoming[:5]:  # Show top 5
            st.write(f"**{milestone['date']}:** {milestone['name']} ({milestone['project']})")
    
    # Quick actions
    st.subheader("Quick Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create New Project"):
            st.session_state.current_view = "Projects"
            st.rerun()
    with col2:
        if st.button("Open AI Assistant"):
            st.session_state.current_view = "AI Assistant"
            st.rerun()

def display_projects():
    """Display the projects view for managing projects"""
    st.title("Projects Management")
    
    # Project creation form
    with st.expander("Create New Project", expanded=len(st.session_state.projects) == 0):
        with st.form("new_project_form"):
            project_name = st.text_input("Project Name")
            project_desc = st.text_area("Description")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date")
            with col2:
                end_date = st.date_input("End Date")
            
            status_options = ["Planning", "Active", "On Hold", "Completed", "Cancelled"]
            project_status = st.selectbox("Status", status_options, index=0)
            
            # Milestone inputs
            st.subheader("Initial Milestones")
            milestone_names = st.text_area("Milestone Names (one per line)")
            milestone_dates = st.text_area("Milestone Dates (one per line, YYYY-MM-DD format)")
            
            submitted = st.form_submit_button("Create Project")
            
            if submitted:
                if not project_name:
                    st.error("Project name is required")
                else:
                    # Process milestones
                    milestones = []
                    names = milestone_names.strip().split('\n') if milestone_names else []
                    dates = milestone_dates.strip().split('\n') if milestone_dates else []
                    
                    for i in range(min(len(names), len(dates))):
                        if names[i].strip() and dates[i].strip():
                            try:
                                # Validate date format
                                datetime.date.fromisoformat(dates[i].strip())
                                milestones.append({
                                    "name": names[i].strip(),
                                    "date": dates[i].strip(),
                                    "status": "Pending"
                                })
                            except ValueError:
                                st.error(f"Invalid date format: {dates[i]}")
                    
                    # Create new project
                    new_project = {
                        "id": len(st.session_state.projects) + 1,
                        "name": project_name,
                        "description": project_desc,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "status": project_status,
                        "progress": 0,
                        "milestones": milestones,
                        "tasks": [],
                        "team": [],
                        "last_updated": datetime.datetime.now().isoformat()
                    }
                    
                    st.session_state.projects.append(new_project)
                    st.success(f"Project '{project_name}' created successfully!")
                    st.rerun()
    
    # Project list
    st.subheader("Your Projects")
    
    if not st.session_state.projects:
        st.info("No projects created yet. Use the form above to create your first project.")
    else:
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            filter_status = st.multiselect(
                "Filter by Status",
                options=["Planning", "Active", "On Hold", "Completed", "Cancelled"],
                default=[]
            )
        with col2:
            sort_option = st.selectbox(
                "Sort by",
                options=["Name", "Start Date", "End Date", "Status", "Progress"],
                index=0
            )
        
        # Apply filters
        filtered_projects = st.session_state.projects
        if filter_status:
            filtered_projects = [p for p in filtered_projects if p["status"] in filter_status]
        
        # Apply sorting
        if sort_option == "Name":
            filtered_projects.sort(key=lambda x: x["name"])
        elif sort_option == "Start Date":
            filtered_projects.sort(key=lambda x: x["start_date"])
        elif sort_option == "End Date":
            filtered_projects.sort(key=lambda x: x["end_date"])
        elif sort_option == "Status":
            filtered_projects.sort(key=lambda x: x["status"])
        elif sort_option == "Progress":
            filtered_projects.sort(key=lambda x: x["progress"], reverse=True)
        
        # Display projects
        for idx, project in enumerate(filtered_projects):
            with st.expander(f"{project['name']} - {project['status']}"):
                tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Milestones", "Tasks", "Team"])
                
                with tab1:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Description:** {project['description']}")
                        st.write(f"**Start Date:** {project['start_date']}")
                        st.write(f"**End Date:** {project['end_date']}")
                    with col2:
                        st.write(f"**Status:** {project['status']}")
                        st.write(f"**Progress:** {project['progress']}%")
                        st.progress(project['progress']/100)
                    
                    # Update project
                    st.subheader("Update Project")
                    new_status = st.selectbox(
                        "Update Status",
                        options=["Planning", "Active", "On Hold", "Completed", "Cancelled"],
                        index=["Planning", "Active", "On Hold", "Completed", "Cancelled"].index(project["status"]),
                        key=f"status_{idx}"
                    )
                    new_progress = st.slider(
                        "Update Progress",
                        0, 100, project["progress"],
                        key=f"progress_{idx}"
                    )
                    if st.button("Update", key=f"update_{idx}"):
                        project["status"] = new_status
                        project["progress"] = new_progress
                        project["last_updated"] = datetime.datetime.now().isoformat()
                        st.success("Project updated successfully!")
                        st.rerun()
                
                with tab2:
                    st.subheader("Milestones")
                    if not project.get("milestones"):
                        st.info("No milestones for this project.")
                    else:
                        # Display existing milestones
                        for midx, milestone in enumerate(project["milestones"]):
                            cols = st.columns([3, 2, 2, 1])
                            with cols[0]:
                                st.write(milestone["name"])
                            with cols[1]:
                                st.write(milestone["date"])
                            with cols[2]:
                                status = st.selectbox(
                                    "Status",
                                    options=["Pending", "In Progress", "Completed", "Delayed"],
                                    index=["Pending", "In Progress", "Completed", "Delayed"].index(milestone["status"]),
                                    key=f"ms_status_{idx}_{midx}"
                                )
                            with cols[3]:
                                update = st.button("✓", key=f"ms_update_{idx}_{midx}")
                                
                            if update:
                                project["milestones"][midx]["status"] = status
                                project["last_updated"] = datetime.datetime.now().isoformat()
                                st.success("Milestone updated!")
                                st.rerun()
                    
                    # Add new milestone
                    st.subheader("Add Milestone")
                    with st.form(key=f"add_milestone_{idx}"):
                        ms_name = st.text_input("Milestone Name", key=f"ms_name_{idx}")
                        ms_date = st.date_input("Date", key=f"ms_date_{idx}")
                        ms_status = st.selectbox(
                            "Status",
                            options=["Pending", "In Progress", "Completed", "Delayed"],
                            index=0,
                            key=f"ms_status_new_{idx}"
                        )
                        submitted = st.form_submit_button("Add Milestone")
                        
                        if submitted:
                            if not ms_name:
                                st.error("Milestone name is required")
                            else:
                                if "milestones" not in project:
                                    project["milestones"] = []
                                
                                project["milestones"].append({
                                    "name": ms_name,
                                    "date": ms_date.isoformat(),
                                    "status": ms_status
                                })
                                project["last_updated"] = datetime.datetime.now().isoformat()
                                st.success("Milestone added!")
                                st.rerun()
                
                with tab3:
                    st.subheader("Tasks")
                    
                    # Display task timeline if tasks exist
                    if project.get("tasks"):
                        timeline_data = {
                            "events": []
                        }
                        
                        for task in project["tasks"]:
                            task_item = {
                                "start_date": {
                                    "year": task["start_date"].split("-")[0],
                                    "month": task["start_date"].split("-")[1],
                                    "day": task["start_date"].split("-")[2]
                                },
                                "end_date": {
                                    "year": task["end_date"].split("-")[0],
                                    "month": task["end_date"].split("-")[1],
                                    "day": task["end_date"].split("-")[2]
                                },
                                "text": {
                                    "headline": task["name"],
                                    "text": f"Assigned to: {task['assignee']}<br>Status: {task['status']}"
                                },
                                "group": task["status"]
                            }
                            timeline_data["events"].append(task_item)
                        
                        if timeline_data["events"]:
                            timeline(timeline_data, height=400)
                    
                    # Display existing tasks
                    if not project.get("tasks"):
                        st.info("No tasks for this project.")
                    else:
                        for tidx, task in enumerate(project["tasks"]):
                            with st.expander(f"{task['name']} - {task['status']}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Description:** {task['description']}")
                                    st.write(f"**Assignee:** {task['assignee']}")
                                with col2:
                                    st.write(f"**Start Date:** {task['start_date']}")
                                    st.write(f"**End Date:** {task['end_date']}")
                                    st.write(f"**Status:** {task['status']}")
                                
                                # Update task
                                new_task_status = st.selectbox(
                                    "Update Status",
                                    options=["Not Started", "In Progress", "Completed", "Blocked"],
                                    index=["Not Started", "In Progress", "Completed", "Blocked"].index(task["status"]),
                                    key=f"task_status_{idx}_{tidx}"
                                )
                                if st.button("Update Status", key=f"task_update_{idx}_{tidx}"):
                                    project["tasks"][tidx]["status"] = new_task_status
                                    project["last_updated"] = datetime.datetime.now().isoformat()
                                    st.success("Task updated!")
                                    st.rerun()
                    
                    # Add new task
                    st.subheader("Add Task")
                    with st.form(key=f"add_task_{idx}"):
                        task_name = st.text_input("Task Name", key=f"task_name_{idx}")
                        task_desc = st.text_area("Description", key=f"task_desc_{idx}")
                        task_assignee = st.text_input("Assignee", key=f"task_assignee_{idx}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            task_start = st.date_input("Start Date", key=f"task_start_{idx}")
                        with col2:
                            task_end = st.date_input("End Date", key=f"task_end_{idx}")
                        
                        task_status = st.selectbox(
                            "Status",
                            options=["Not Started", "In Progress", "Completed", "Blocked"],
                            index=0,
                            key=f"task_status_new_{idx}"
                        )
                        submitted = st.form_submit_button("Add Task")
                        
                        if submitted:
                            if not task_name:
                                st.error("Task name is required")
                            else:
                                if "tasks" not in project:
                                    project["tasks"] = []
                                
                                project["tasks"].append({
                                    "name": task_name,
                                    "description": task_desc,
                                    "assignee": task_assignee,
                                    "start_date": task_start.isoformat(),
                                    "end_date": task_end.isoformat(),
                                    "status": task_status
                                })
                                project["last_updated"] = datetime.datetime.now().isoformat()
                                st.success("Task added!")
                                st.rerun()
                
                with tab4:
                    st.subheader("Team Members")
                    
                    # Display existing team members
                    if not project.get("team"):
                        st.info("No team members assigned to this project.")
                    else:
                        for tmidx, member in enumerate(project["team"]):
                            cols = st.columns([2, 2, 2, 1])
                            with cols[0]:
                                st.write(member["name"])
                            with cols[1]:
                                st.write(member["role"])
                            with cols[2]:
                                st.write(member["email"])
                            with cols[3]:
                                if st.button("🗑", key=f"remove_tm_{idx}_{tmidx}"):
                                    project["team"].pop(tmidx)
                                    project["last_updated"] = datetime.datetime.now().isoformat()
                                    st.success("Team member removed!")
                                    st.rerun()
                    
                    # Add new team member
                    st.subheader("Add Team Member")
                    with st.form(key=f"add_team_{idx}"):
                        member_name = st.text_input("Name", key=f"tm_name_{idx}")
                        member_role = st.text_input("Role", key=f"tm_role_{idx}")
                        member_email = st.text_input("Email", key=f"tm_email_{idx}")
                        submitted = st.form_submit_button("Add Team Member")
                        
                        if submitted:
                            if not member_name:
                                st.error("Name is required")
                            else:
                                if "team" not in project:
                                    project["team"] = []
                                
                                project["team"].append({
                                    "name": member_name,
                                    "role": member_role,
                                    "email": member_email
                                })
                                project["last_updated"] = datetime.datetime.now().isoformat()
                                st.success("Team member added!")
                                st.rerun()

def display_ai_assistant():
    """Display the AI Assistant view for project management assistance"""
    st.title("Project Management AI Assistant")
    
    client = anthropic.Anthropic(
        api_key=st.secrets["ANTHROPIC_API_KEY"],
    )
    
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
    
    # Project context selector
    st.subheader("Project Context")
    if st.session_state.projects:
        project_names = ["None"] + [p["name"] for p in st.session_state.projects]
        selected_project = st.selectbox(
            "Select a project for context",
            options=project_names,
            index=0
        )
        
        if selected_project != "None":
            # Find selected project
            project = next((p for p in st.session_state.projects if p["name"] == selected_project), None)
            if project:
                st.session_state.current_project = project
                
                # Display project info
                st.write(f"**Project:** {project['name']}")
                st.write(f"**Status:** {project['status']} ({project['progress']}% complete)")
                st.write(f"**Timeline:** {project['start_date']} to {project['end_date']}")
                
                # Add project context to canvas
                if st.button("Add Project Context to Prompt"):
                    project_context = f"""
                    Project Name: {project['name']}
                    Description: {project['description']}
                    Status: {project['status']}
                    Progress: {project['progress']}%
                    Timeline: {project['start_date']} to {project['end_date']}
                    """
                    
                    # Add milestones
                    if project.get("milestones"):
                        project_context += "\n\nMilestones:\n"
                        for milestone in project["milestones"]:
                            project_context += f"- {milestone['name']} ({milestone['date']}): {milestone['status']}\n"
                    
                    # Add tasks
                    if project.get("tasks"):
                        project_context += "\n\nTasks:\n"
                        for task in project["tasks"]:
                            project_context += f"- {task['name']} ({task['status']}): Assigned to {task['assignee']}\n"
                    
                    # Add team
                    if project.get("team"):
                        project_context += "\n\nTeam:\n"
                        for member in project["team"]:
                            project_context += f"- {member['name']} ({member['role']})\n"
                    
                    if "canvas_text" not in st.session_state:
                        st.session_state.canvas_text = ""
                    
                    # Add context to canvas
                    if st.session_state.canvas_text:
                        st.session_state.canvas_text += "\n\n--- Project Context ---\n" + project_context
                    else:
                        st.session_state.canvas_text = "--- Project Context ---\n" + project_context
                    
                    st.success("Project context added to prompt!")
    else:
        st.info("No projects available. Create a project in the Projects tab to use project context.")
    
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
            full_response = ""
            
            # Define the output guidelines
            OUTPUT_GUIDELINES = '''
            BLOCK CATEGORY:
                - Promoting violence, illegal activities, or hate speech
                - Explicit sexual content
                - Harmful misinformation or conspiracy theories
            
                ALLOW CATEGORY:
                - Most other content is allowed, as long as it is not explicitly disallowed
            '''
            
            # Stream the response
            try:
                with client.messages.stream(
                    max_tokens=int(st.secrets["MAX_TOKENS"]),
                    system=st.session_state.ai_system_prompt + f"\n\nPlease adhere to these output guidelines: {OUTPUT_GUIDELINES}",
                    messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                    model=st.session_state.ai_model,
                ) as stream:
                    for text in stream.text_stream:
                        full_response += str(text) if text is not None else ""
                        message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
            except Exception as e:
                st.error(f"Error: {str(e)}")
                full_response = "I apologize, but I encountered an error. Please try again."
                message_placeholder.markdown(full_response)
            
            # Add the response to chat history
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        # Clear the canvas after sending
        st.session_state.canvas_text = ""

def display_documents():
    """Display the documents view for managing project documents"""
    st.title("Project Documents")
    
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
        
        # Associate with project
        project_names = ["None"] + [p["name"] for p in st.session_state.projects]
        associated_project = st.selectbox("Associate with Project", options=project_names)
        
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
                "associated_project": None if associated_project == "None" else associated_project,
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
        col1, col2 = st.columns(2)
        with col1:
            filter_type = st.multiselect(
                "Filter by Type",
                options=["Requirements", "Plan", "Report", "Meeting Minutes", "Other"],
                default=[]
            )
        with col2:
            filter_project = st.multiselect(
                "Filter by Project",
                options=["None"] + [p["name"] for p in st.session_state.projects],
                default=[]
            )
        
        # Apply filters
        filtered_docs = st.session_state.documents
        if filter_type:
            filtered_docs = [d for d in filtered_docs if d["type"] in filter_type]
        if filter_project:
            project_filter = ["None" if p == "None" else p for p in filter_project]
            filtered_docs = [d for d in filtered_docs if d["associated_project"] in project_filter]
        
        # Display documents
        for doc in filtered_docs:
            with st.expander(f"{doc['name']} ({doc['type']})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Type:** {doc['type']}")
                    st.write(f"**Description:** {doc['description'] if doc['description'] else 'No description'}")
                    st.write(f"**Upload Date:** {doc['upload_date'].split('T')[0]}")
                with col2:
                    st.write(f"**Project:** {doc['associated_project'] if doc['associated_project'] else 'None'}")
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
