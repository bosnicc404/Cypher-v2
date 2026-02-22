# === CYPHER V2 ===
#---- 1. add a new feature
#---- 2. ask cypher what he thinks
#---- 3. ask him for more features
#---- 4. add his features
#---- 5. test his features
#---- 6. repeat

#----imports----#
import os
import json
import asyncio
import subprocess
import shutil
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras
from system_info import get_system_summary
from voice import speak, WakeWord, record_until_silence, transcribe
#---------------#

#----CEREBRAS BACKEND----#
load_dotenv()
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

client = Cerebras(api_key=CEREBRAS_API_KEY)

SYSTEM_PROMPT = "You are Cypher, my personal AI assistant that controls my Fedora Linux computer. Speak in a humorous Gen Z tone. When asked to open any app or website, respond with ONLY this exact JSON, no extra text before or after: {\"action\": \"open\", \"target\": \"app_name_or_url\", \"response\": \"your funny one liner\"}. For system info use: {\"action\": \"info\", \"response\": \"funny one liner\"}. For volume control use: {\"action\": \"volume\", \"direction\": \"up/down\", \"amount\": \"depends, but generally between 5-10%\", \"response\": \"funny one liner\"}. For file reading, use {\"action\": \"read_file\", \"target\": \"/path/to/file\", \"response\": \"funny one liner\"}. For writing/editing code use: {\"action\": \"write_file\", \"target\": \"/path/to/file\", \"content\": \"the actual code\", \"response\": \"funny one liner\"}.Your code handles everything else, trust the process. For normal conversation just chat normally."

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
        elif data["action"] == "info":
            return get_system_summary()
        elif data["action"] == "write_file":
            allowed_path = "/home/bosnicc/code/ai"
            if not data["target"].startswith(allowed_path):
                return "nah Cypher tried to write outside the project folder 🚫"
            mode = data.get("mode", "w")
            with open(data["target"], mode) as f:
                f.write(data["content"])
        
        return data["response"]
    except Exception as e:
        print(f"DEBUG error: {e}")
        return reply

async def voice_mode():
    wd = WakeWord()
    print("[Cypher] Voice mode active, say 'Cypher' to wake me up 👂")
    current_speech = None
    while True:
        await wd.wait()
        
        if current_speech and not current_speech.done():
            current_speech.cancel()
            try:
                await current_speech
            except asyncio.CancelledError:
                pass
        
        audio = record_until_silence()
        user_input = transcribe(audio)
        if user_input:
            print(f"You: {user_input}")
            response = execute_command(chat(user_input))
            print(f"Cypher: {response}")
            current_speech = asyncio.create_task(speak(response))

def text_mode():
    print("[Cypher] Text mode active, type away 💬")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "end"]:
            break
        print(f"Cypher: {execute_command(chat(user_input))}")

print("Choose mode: [1] Text  [2] Voice")
choice = input("> ")

if choice == "2":
    asyncio.run(voice_mode())
else:
    text_mode()
