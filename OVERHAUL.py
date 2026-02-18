# === CYPHER V2 ===
#---- 1. voice input (whisper/vosk)
#---- 2. send to cerebras
#---- 3. parse response for OS commands
#---- 4. execute command
#----5. voice output (edge-tts)
#---- 6. repeat

#----imports----#
import os
import json
import subprocess
import shutil
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras
#---------------#

#----CEREBRAS BACKEND----#
load_dotenv()
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

client = Cerebras(api_key=CEREBRAS_API_KEY)

SYSTEM_PROMPT = "You are Cypher, my personal AI assistant that controls my Fedora Linux computer. Speak in a humorous Gen Z tone. When asked to open any app or website, respond with ONLY this exact JSON, no extra text before or after: {\"action\": \"open\", \"target\": \"app_name_or_url\", \"response\": \"your funny one liner\"}. For volume control use: {\"action\": \"volume\", \"direction\": \"up/down\", \"amount\": \"depends, but generally between 5-10%\", \"response\": \"funny one liner\"}. For file reading, use {\"action\": \"read_file\", \"target\": \"/path/to/file\", \"response\": \"funny one liner\"}. For writing/editing code use: {\"action\": \"write_file\", \"target\": \"/path/to/file\", \"content\": \"the actual code\", \"response\": \"funny one liner\"}.Your code handles everything else, trust the process. For normal conversation just chat normally."
history = []

def chat(user_input):
    history.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model="gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *history
        ],
        max_tokens=1024
    )
    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    return reply

def get_launch_command(target):
    if shutil.which(target.lower()):
        return [target.lower()]
    result = subprocess.run(["/usr/bin/flatpak", "list", "--app", "--columns=application"], 
                          capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if target.lower() in line.lower():
            return ["flatpak", "run", line.strip()]
    return None

def execute_command(reply):
    if "{" not in reply:
        return reply
    try:
        start = reply.index("{")
        end = reply.rindex("}") + 1
        json_str = reply[start:end]
        data = json.loads(json_str)
        
        if data["action"] == "open":
            target = data["target"]
            cmd = get_launch_command(target)
            if cmd:
                subprocess.Popen(cmd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            else:
                subprocess.Popen(["xdg-open", target], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        elif data["action"] == "volume":
            direction = "+" if data["direction"] == "up" else "-"
            amount = data.get("amount", "10%")
            subprocess.run(f"pactl set-sink-volume @DEFAULT_SINK@ {direction}{amount}", shell=True, stderr=subprocess.DEVNULL)
        elif data["action"] == "read_file":
            with open(data["target"], "r") as f:
                content = f.read()
            history.append({"role": "system", "content": f"File contents:\n{content}"})
        elif data["action"] == "write_file":
            allowed_path = "/home/bosnicc/code/ai"
            if not data["target"].startswith(allowed_path):
                return "nah Cypher tried to write outside the project folder 🚫"
            with open(data["target"], "w") as f:
                f.write(data["content"])
        
        return data["response"]
    except Exception as e:
        print(f"DEBUG error: {e}")
        return reply
    
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit", "end"]:
        break
    print(f"Cypher: {execute_command(chat(user_input))}")
