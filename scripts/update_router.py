path = r"f:\ROBOVAI BOT\app\ui\web.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

new_content = content.replace("@router.", "@protected_router.")

with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)
