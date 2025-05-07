import streamlit as st
from openai import OpenAI
import json
import uuid

# App Configuration
st.set_page_config(page_title="EchoDraft Dashboard", layout="wide")
st.markdown("""
    <style>
    body {background-color: #f5f7fa;}
    .main {background: linear-gradient(145deg, #ffffff, #e6e9ef); border-radius: 20px; padding: 30px; box-shadow: 0 4px 30px rgba(0,0,0,0.1);}
    .stTextArea textarea {border-radius: 10px;}
    .stButton>button {border-radius: 10px; padding: 0.5em 1.2em; font-weight: bold; background: #5e60ce; color: white; border: none;}
    .stSelectbox div {border-radius: 10px;}
    .stMarkdown, .stExpander {background: white; border-radius: 15px; padding: 15px; margin-bottom: 10px;}
    .stExpanderHeader {font-weight: 600; font-size: 1.1em;}
    </style>
""", unsafe_allow_html=True)

# Initialize OpenAI
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# App State
if "memory_vault" not in st.session_state:
    st.session_state.memory_vault = []
if "timeline_order" not in st.session_state:
    st.session_state.timeline_order = []

st.title("📘 EchoDraft – Your Personal Memoir Workspace")

with st.container():
    st.subheader("1. Write or Paste a Memory")
    memory_text = st.text_area("Memory", placeholder="Describe a moment from your life in vivid detail...", height=200)

if memory_text:
    st.subheader("2. Select a Reflective Persona")
    persona = st.selectbox("Choose a perspective: ", ["Therapist", "Editor", "Friend", "Skeptic"])
    persona_prompts = {
        "Therapist": "You are a therapist offering thoughtful, deep follow-up questions about the user's experience.",
        "Editor": "You are a professional editor helping refine and organize a memoir.",
        "Friend": "You are a warm friend, asking thoughtful, curious questions.",
        "Skeptic": "You are a sharp interviewer, asking tough, clarifying questions."
    }

    if st.button("🎙️ Generate Follow-Up Questions"):
        with st.spinner("Thinking like a " + persona + "..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": persona_prompts[persona]},
                        {"role": "user", "content": f"Memory:\n{memory_text}\n\nAsk 2–3 thoughtful follow-up questions."}
                    ]
                )
                follow_up = response.choices[0].message.content.strip()
                st.session_state.follow_up = follow_up
                st.success("Generated follow-up questions!")
                st.markdown(f"**{persona} asks:**\n\n{follow_up}")
            except Exception as e:
                st.error(f"Error generating follow-up: {e}")

if "follow_up" in st.session_state:
    user_reply = st.text_area("Your Reply to the Questions", height=150)

    if st.button("🧠 Analyze & Save to Timeline"):
        with st.spinner("Organizing your memory with tags..."):
            try:
                tag_prompt = f"""
You are a storytelling assistant. Extract the following from the user's memory:
- Key people
- Places
- Main emotion (1–2 words)
- Themes (reuse recurring tags when possible, create new ones when appropriate)

Memory:
{memory_text}

Format:
{{
"people": [...],
"places": [...],
"emotion": "...",
"tags": [...]
}}
"""
                tag_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": tag_prompt}]
                )
                tag_output = tag_response.choices[0].message.content.strip()
                tags = json.loads(tag_output)

                memory_id = str(uuid.uuid4())
                memory_entry = {
                    "id": memory_id,
                    "memory": memory_text,
                    "persona": persona,
                    "follow_up": st.session_state.follow_up,
                    "user_response": user_reply,
                    "tags": tags
                }

                st.session_state.memory_vault.append(memory_entry)
                st.session_state.timeline_order.append(memory_id)
                st.success("Saved successfully to your timeline ✨")

            except Exception as e:
                st.error(f"Error saving memory: {e}")

st.subheader("🧭 3. Explore Your Timeline")
if st.session_state.memory_vault:
    tag_filter = st.multiselect("Filter by Tag", sorted({tag for m in st.session_state.memory_vault for tag in m['tags']['tags']}))

    filtered_ids = [m["id"] for m in st.session_state.memory_vault
                    if not tag_filter or any(tag in m["tags"]["tags"] for tag in tag_filter)]

    reorder = st.multiselect(
        "Reorder memories:",
        options=filtered_ids,
        default=st.session_state.timeline_order,
        format_func=lambda idx: next((m["tags"]["emotion"] + " – " + m["memory"][:30] for m in st.session_state.memory_vault if m["id"] == idx), idx)
    )

    st.session_state.timeline_order = reorder

    for i, mem_id in enumerate(reorder):
        m = next((m for m in st.session_state.memory_vault if m["id"] == mem_id), None)
        if m:
            with st.expander(f"{i + 1}. {m['tags']['emotion']} – {', '.join(m['tags']['tags'])}", expanded=False):
                st.markdown(f"**Memory:** {m['memory']}")
                st.markdown(f"**{m['persona']} asked:** {m['follow_up']}")
                st.markdown(f"**Your Response:** {m['user_response']}")
                st.markdown(f"**People:** {', '.join(m['tags']['people'])}")
                st.markdown(f"**Places:** {', '.join(m['tags']['places'])}")
""