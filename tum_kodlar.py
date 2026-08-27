import os

with open("tum_kodlar.txt", "w", encoding="utf-8") as outfile:
    for root, _, files in os.walk("."):
        if any(x in root for x in [".git", "__pycache__", "venv"]):
            continue
        for file in files:
            if file.endswith(".py") or file in ["requirements.txt", "config.py"]:
                path = os.path.join(root, file)
                outfile.write(f"\n{'='*20} {path} {'='*20}\n\n")
                with open(path, "r", encoding="utf-8", errors="ignore") as infile:
                    outfile.write(infile.read())
                    outfile.write("\n")

print("tum_kodlar.txt basariyla olusturuldu!")
