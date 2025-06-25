import os

def scan_for_inter():
    print("👁️ Scanning for 'inter-display' references...\n")
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith((".html", ".css", ".js")):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for idx, line in enumerate(f, 1):
                        if "inter-display" in line.lower():
                            print(f"⚠️  {path} (line {idx}): {line.strip()}")

def clean_dead_inter_links():
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith((".html", ".css")):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                new_lines = [
                    line for line in lines
                    if "inter-display" not in line.lower() or not line.strip().startswith("<!--")
                ]
                if len(new_lines) < len(lines):
                    with open(path, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                    print(f"🧹 Cleaned: {path}")
