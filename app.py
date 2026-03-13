import streamlit as st
from groq import Groq

st.title("Archimedes")

# Groq client
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# default model
if "model" not in st.session_state:
    st.session_state.model = "openai/gpt-oss-120b"

# chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# show previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# user input
if prompt := st.chat_input("Ask something"):

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        response = client.chat.completions.create(
            model=st.session_state.model,
            messages=st.session_state.messages,
        )

        reply = response.choices[0].message.content
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
