"""
    Interacts with a local IPFS daemon via HTTP. It persistently stores and retrieves data from Etherscan Agent, creating a decentralized history of all queries.

    Features:
        - Uploads json file to IPFS network.
        - Retrieves data from existing json file.
        - Appends new data to existing json file.
        - Has persistence via creating a local 'CID' file to track the CID over time.

    Requires:
        - Local IPFS daemon running. (The command to run is 'ipfs daemon')

"""
import json
import time
import requests
from typing import Dict, Any, Optional

class IPFSUploader:
    def __init__(self, api_url: str = "http://127.0.0.1:5001"):
        """
        Connects to the IPFS HTTP API.
        """
        self.api_url = api_url
        self.session = requests.Session()

    def get_cid_from_file(self, filename: str = "CID") -> Optional[str]:
        """
        Reads the CID from a local file. Creates file if it doesn't exist.
        """
        try:
            with open(filename, 'r') as f:
                cid = f.read().strip()
                return cid if cid else None
        except FileNotFoundError:
            # Create empty file
            with open(filename, 'w') as f:
                f.write("")
            return None
        except Exception as e:
            print(f"[IPFS] Error reading CID file: {e}")
            return None

    def update_cid_file(self, cid: str, filename: str = "CID"):
        """
        Updates the CID file with the new CID.
        """
        try:
            with open(filename, 'w') as f:
                f.write(cid)
            print(f"[IPFS] Updated CID File with: {cid}")
        except Exception as e:
            print(f"[IPFS] Error updating CID file: {e}")

    def fetch_from_ipfs(self, cid: str) -> Optional[Dict[str, Any]]:
        """
        Fetches JSON data from IPFS by CID.
        """
        try:
            url = f"https://ipfs.io/ipfs/{cid}"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[IPFS] Failed to fetch from IPFS: {response.status_code}")
                return None
        except Exception as e:
            print(f"[IPFS] Error fetching from IPFS: {e}")
            return None

    def upload_execution_log(self, payload: Dict[str, Any], 
                             append_to_history: bool = False) -> Optional[str]:
        """
        Uploads data to IPFS.

        If append_to_history=True:
            1. Fetches the existing history JSON from IPFS using the stored CID.
            2. Appends the new payload to results array.
            3. Re-uploads the combined JSON as a new file.
            4. Updates the local 'CID' file with the new hash.
        """
        try:
            # If appending to history, load existing data first
            if append_to_history:
                existing_cid = self.get_cid_from_file()
                
                if existing_cid:
                    history = self.fetch_from_ipfs(existing_cid)
                    if history and "results" in history:
                        history["results"].append(payload)
                        json_data = json.dumps(history, indent=2, default=str)
                    else:
                        # Invalid existing data, start fresh
                        history = {"results": [payload]}
                        json_data = json.dumps(history, indent=2, default=str)
                else:
                    # No existing history, create new
                    history = {"results": [payload]}
                    json_data = json.dumps(history, indent=2, default=str)
            else:
                # Original behavior - single payload
                json_data = json.dumps(payload, indent=2, default=str)
            
            files = {
                "file": ("execution_log.json", json_data.encode("utf-8"))
            }
            params = {"pin": "true"}
            url = f"{self.api_url}/api/v0/add"
            
            print(f"[IPFS] Attempting upload to {url}...")
            
            response = self.session.post(url, files=files, params=params, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if isinstance(result, list) and len(result) > 0:
                    cid = result[0]["Hash"]
                elif isinstance(result, dict) and "Hash" in result:
                    cid = result["Hash"]
                else:
                    print(f"[IPFS] Unexpected response format: {result}")
                    return None
                
                print(f"[IPFS] SUCCESS! Uploaded to IPFS.")
                print(f"[IPFS] CID: {cid}")
                print(f"[IPFS] View link: https://ipfs.io/ipfs/{cid}")
                
                # Update CID file if appending to history
                if append_to_history:
                    self.update_cid_file(cid)
                
                return cid
            else:
                print(f"[IPFS] FAILED: Status {response.status_code}")
                print(f"[IPFS] Response: {response.text}")
                return None

        except requests.exceptions.ConnectionError:
            print(f"[IPFS] ERROR: Could not connect to IPFS daemon at {self.api_url}")
            print(f"[IPFS] Make sure 'ipfs daemon' is running.")
            return None
        except Exception as e:
            print(f"[IPFS] ERROR: {e}")
            return None

    def close(self):
        self.session.close()

# Helper to integrate with agent
def integrate_with_agent(question: str, tool_name: str, tool_input: str, tool_output: str, final_answer: str) -> str:
    payload = {
        "question": question,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_output": tool_output,
        "final_answer": final_answer,
        "timestamp": time.time()
    }

    uploader = IPFSUploader()
    cid = uploader.upload_execution_log(payload)
    
    if cid:
        return f"Execution stored on IPFS. CID: {cid}"
    else:
        return "Failed to store on IPFS."

if __name__ == "__main__":
    # Test
    test_payload = {
        "question": "Test Question",
        "tool_name": "test_tool",
        "tool_input": "",
        "tool_output": "test output",
        "final_answer": "The answer is 42.",
        "timestamp": time.time()
    }
    print(integrate_with_agent(**test_payload))