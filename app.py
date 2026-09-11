import streamlit as st
import sys
import io
from contextlib import redirect_stdout
from agent import create_agent

st.set_page_config(page_title="AutoAgent.AI", page_icon="🤖", layout="wide")

st.title("🤖 AutoAgent.AI: Autonomous Desktop Automation using Qwen 2.5")
st.markdown("Execute Python tasks safely inside a Docker sandbox.")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    mode = st.radio("Execution Mode", ["global", "local"], index=0, help="Global uses Hugging Face API. Local runs on your GPU.")
    env = st.radio("Execution Environment", ["Docker Sandbox", "Windows Host (Native)"], index=0, help="Run safely in Docker, or directly on your real Windows machine.")
    model_id = st.text_input("Custom Model ID (Optional)", value="", help="Leave blank for defaults.")
    
    use_docker = (env == "Docker Sandbox")
    import os
    default_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    
    if use_docker:
        auth_dirs_raw = st.text_area("Authorized Directories (One per line)", value=default_dir, help="These host directories will be securely mounted into the sandbox.")
    else:
        st.info("⚠️ Agent will run directly on your Windows host. All files are accessible.")
        auth_dirs_raw = ""

# Main interface
prompt = st.text_area("What would you like the agent to do?", height=150, placeholder="e.g., Find all screenshots on my desktop taken today and move them to a new folder named 'Current_Project'.")

if st.button("Run Agent", type="primary"):
    if not prompt.strip():
        st.warning("Please enter a prompt.")
    else:
        # Step 1: Initialize Agent
        with st.spinner(f"Initializing {mode} agent in {env}..."):
            try:
                # Use empty string for model_id if not provided
                m_id = model_id.strip() if model_id.strip() else None
                authorized_dirs = [d.strip() for d in auth_dirs_raw.splitlines() if d.strip()] if use_docker else None
                
                agent, sandbox = create_agent(mode=mode, model_id=m_id, authorized_dirs=authorized_dirs, use_docker=use_docker)
            except Exception as e:
                st.error(f"Failed to initialize agent: {e}")
                st.stop()
                
        # Step 2: Run Agent and Capture Logs
        st.subheader("Live Execution Logs")
        log_expander = st.expander("Agent Thinking Process...", expanded=True)
        log_placeholder = log_expander.empty()
        
        class StreamlitLogStream(io.StringIO):
            def __init__(self, placeholder):
                super().__init__()
                self.placeholder = placeholder
                import re
                self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                
            def write(self, text):
                super().write(text)
                # Update the UI live
                raw_logs = self.getvalue()
                clean_logs = self.ansi_escape.sub('', raw_logs)
                # Show up to last 4000 characters to prevent browser UI lag during heavy streaming
                display_text = clean_logs[-4000:] if len(clean_logs) > 4000 else clean_logs
                self.placeholder.code(display_text, language="text")
                
        log_capture = StreamlitLogStream(log_placeholder)
        
        with redirect_stdout(log_capture):
            try:
                result = agent.run(prompt)
            except Exception as e:
                result = f"Error during execution: {e}"
        
        # Step 3: Display Results
        st.subheader("Final Result")
        result_lower = str(result).lower()
        if "error" in result_lower or "fail" in result_lower or "not found" in result_lower or "could not" in result_lower:
            st.error(result)
        else:
            st.success(result)
        
        # Step 4: Upgrade logs to full-color HTML after completion
        raw_logs = log_capture.getvalue()
        
        # Shorten excessively long decorative terminal lines for a cleaner web UI
        import re
        raw_logs = re.sub(r'─{10,}', '───', raw_logs)
        raw_logs = re.sub(r'━{10,}', '━━━', raw_logs)
        
        try:
            from ansi2html import Ansi2HTMLConverter
            
            # Convert the raw ANSI terminal logs directly to styled HTML
            conv = Ansi2HTMLConverter(dark_bg=True)
            html_logs = conv.convert(raw_logs)
            
            # Replace the plain text live-stream with the beautiful HTML version
            log_placeholder.empty()
            with log_expander:
                st.markdown(html_logs, unsafe_allow_html=True)
        except ImportError:
            # Fallback to plain text if ansi2html isn't installed
            clean_logs = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', raw_logs)
            log_placeholder.code(clean_logs, language="text")
            st.warning("💡 Tip: Run `pip install ansi2html` to see the beautiful terminal colors in this UI!")
