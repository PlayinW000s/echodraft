import streamlit as st
from openai import OpenAI
import os
import json
import tempfile
from audio_recorder_streamlit import audio_recorder

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# Page config
st.set_page_config(page_title="EchoDraft 2.5", layout="wide")

# Session setup
if "memory_vault" not in st.session_state:
    st.session_state.memory_vault = []
if "timeline_order" not in st.session_state:
    st.session_state.timeline_order = []

st.title("EchoDraft 2.5 – Voice Memoir Builder with Timeline")

# Step 1: Audio Recording
st.header("1. Record Your Memory")
audio_bytes = audio_recorder(pause_threshold=3.0)

if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        audio_path = f.name

    # Step 2: Transcribe Audio
    st.header("2. Transcribe Your Memory")
    with st.spinner("Transcribing using Whisper..."):
        with open(audio_path, "rb") as file:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=file
            )
            memory_text = result.text
        st.success("Transcription Complete")
        st.text_area("Transcribed Memory", memory_text, height=200)

    # Step 3: Persona Selection
    st.header("3. Choose a Persona")
    persona = st.selectbox("Who should reflect with you?", ["Therapist", "Editor", "Friend", "Skeptic"])
    persona_prompts = {
        "Therapist": "You are a therapist offering thoughtful, deep follow-up questions about the user's experience.",
        "Editor": "You are a professional editor helping refine and organize a memoir.",
        "Friend": "You are a warm friend, asking thoughtful, curious questions.",
        "Skeptic": "You are a sharp interviewer, asking tough, clarifying questions."
    }

    # Step 4: Generate Follow-Up
    st.header("4. AI Follow-Up")
    if st.button("Ask Follow-Up Questions"):
        messages = [
            {"role": "system", "content": persona_prompts[persona]},
            {"role": "user", "content": f"This is the user's memory:\n\n{memory_text}\n\nAsk 2–3 helpful follow-up questions."}
        ]
        reply = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        follow_up = reply.choices[0].message.content
        st.markdown(f"**{persona} asks:**")
        st.write(follow_up)

        user_reply = st.text_area("Your Response", placeholder="Write your reply to the AI here...")

        # Step 5: Tagging and Response
        if st.button("Analyze & Save"):
            tag_prompt = f"""
You are a personal storytelling assistant. Extract the following from the user's memory:
- Key people
- Places
- Main emotion (1–2 words)
- Themes (reuse recurring tags when possible, create new ones when appropriate)

Memory:
"""{memory_text}"""

Format:
{{
"people": [...],
"places": [...],
"emotion": "...",
"tags": [...]
}}
"""
            tag_data = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": tag_prompt}],
                temperature=0.5
            )
            structured = eval(tag_data.choices[0].message.content)

            memory_id = len(st.session_state.memory_vault)
            memory_entry = {
                "id": memory_id,
                "memory": memory_text,
                "persona": persona,
                "follow_up": follow_up,
                "user_response": user_reply,
                "tags": structured
            }
            st.session_state.memory_vault.append(memory_entry)
            st.session_state.timeline_order.append(memory_id)
            st.success("Saved to your Memory Vault!")

# Step 6: Timeline Viewer
st.header("5. Visual Timeline Builder")
if st.session_state.memory_vault:
    order = st.session_state.timeline_order
    new_order = st.multiselect(
        "Reorder scenes (drag or select in new sequence):",
        options=order,
        default=order,
        format_func=lambda idx: f"{idx + 1}: {st.session_state.memory_vault[idx]['tags']['emotion']} – {st.session_state.memory_vault[idx]['memory'][:40]}..."
    )
    st.session_state.timeline_order = new_order

    for i, idx in enumerate(new_order):
        m = st.session_state.memory_vault[idx]
        with st.expander(f"{i + 1}. {m['tags']['emotion']} – Tags: {', '.join(m['tags']['tags'])}"):
            st.markdown(f"**Memory:** {m['memory']}")
            st.markdown(f"**{m['persona']} asked:** {m['follow_up']}")
            st.markdown(f"**Your Response:** {m['user_response']}")
            st.markdown(f"**People:** {', '.join(m['tags']['people'])}")
            st.markdown(f"**Places:** {', '.join(m['tags']['places'])}")
