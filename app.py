# app.py
#
# Simple Streamlit UI for the Etherscan + Ollama + IPFS agent.
# - User types a question
# - Backend calls ask_etherscan_agent()
# - Answer is shown in the UI

import streamlit as st
from etherscan_agent import ask_etherscan_agent

st.set_page_config(page_title="Etherscan Agent", page_icon="🧠")

st.title("Etherscan Agent (Ollama + LangChain + IPFS)")
st.write(
    "Ask natural-language questions about Ethereum mainnet using Etherscan data with outputs uploaded to IPFS.\n\n"
    "- Example: `How many transactions are in the most recent Ethereum block?`\n"
    "- Example: `Summarize the latest block`\n"
    "- Example: `What is the latest Ethereum block number?`\n"
    "- Example: `What is the current Ethereum gas price?`\n"
)

with st.form(key="question_form"):
    question = st.text_input(
        "Enter your question",
        placeholder="e.g. What is the latest Ethereum block number?",
    )
    submit = st.form_submit_button(label="Ask Etherscan Agent")

if submit:                      
    if not question.strip():
        st.warning("Please enter a question first.")
    else:
        with st.spinner("Thinking... contacting Etherscan via your agent..."):
            try:
                result = ask_etherscan_agent(question)

                if isinstance(result, dict):
                    answer = result.get("answer", str(result))
                    ipfs_cid = result.get("ipfs_cid")
                else:
                    answer = str(result)
                    ipfs_cid = None

                st.success("Answer:")
                st.write(answer)

                if ipfs_cid:
                    st.info("Execution logged to IPFS:")
                    ipfs_url = f"https://ipfs.io/ipfs/{ipfs_cid}"
                    st.markdown(f"**CID:** `{ipfs_cid}`")
                    st.link_button("View on IPFS", ipfs_url)

            except Exception as e:
                st.error(f"Error while calling the agent: {e}")
