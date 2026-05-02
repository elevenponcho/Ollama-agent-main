Etherscan Agent (Ollama + LangChain + Streamlit + IPFS)

An intelligent Ethereum assistant powered by Ollama (local LLM), LangChain tools, IPFS, and Etherscan API.
Ask natural-language questions about Ethereum mainnet, and the agent will dynamically call tools to fetch the correct data. 
It will then sync with IPFS to provide a decentralized history of requests saved on a JSON file.

Based on code by Roopa, Yashwanth, Rohith.



Features:

Query Ethereum using plain English.

Powered by a local LLM running on your machine (Ollama + Llama 3.2).

LangChain agent intelligently decides which tool to call.

Automatic uploading of input and output to IPFS network. Can fetch and update between agent sessions when IPFS server is running.

Fully interactive Streamlit UI.


Support for wide range of Ethereum questions:
    Latest block info
    Miner address
    Transaction count
    Gas used
    Much more (via modular Etherscan tools)



📦 Installation (macOS)

1️⃣ Install Ollama (LLM engine)

Download for macOS:
    https://ollama.com/download

Open the Ollama.app. This automatically starts the local server on:
    http://localhost:11434

Pull the Llama 3.2 model: 

        ollama pull llama3.2:3b

2️⃣ Install IPFS

Download for macOS:
    https://docs.ipfs.tech/install/ipfs-desktop/

You can begin running your IPFS daemon by opening a new terminal window and running:

        ipfs daemon


3️⃣ Clone your repository: 

        git clone https://github.com/elevenponcho/Ollama-agent-main.git
        cd Ollama-agent-main

4️⃣ Create a virtual environment: 

        python3 -m venv venv
        source venv/bin/activate

5️⃣ Install dependencies:

Make sure that pip is up-to-date:

        python3 -m pip install --upgrade pip

Then install dependencies: 

        pip install langchain==0.2.16 langchain-core==0.2.38 langchain-community==0.2.16 streamlit requests ipfshttpclient

6️⃣ Add your Etherscan API key:

Edit etherscan_agent.py:

        ETHERSCAN_API_KEY = "YOUR_API_KEY_HERE"

(Do NOT commit real API keys to GitHub!)





▶️ Running the Project:

1️⃣ Open the Ollama.app. This automatically starts the local server on: http://localhost:11434

2️⃣ Start IPFS by openinging a new terminal window and running:

    ipfs daemon

3️⃣ Activate virtual environment:  

    source venv/bin/activate

4️⃣ Start the Streamlit UI:

    streamlit run app.py

5️⃣ Open the link:
    http://localhost:8501



🖥️ Agent UI Preview:

<img src="https://github.com/elevenponcho/Ollama-agent-main/blob/main/Agent%20UI%20Example.png" alt="Agent UI Example">

🖥️ Usage Example:
<img src="https://github.com/elevenponcho/Ollama-agent-main/blob/main/Usage%20Example.png" alt="Usage Example">

🖥️ IPFS JSON Output File Example:
<img src="https://github.com/elevenponcho/Ollama-agent-main/blob/main/IPFS%20JSON%20Output%20With%20Multiple%20Queries.png" alt="IPFS JSON Output With Multiple Queries">
