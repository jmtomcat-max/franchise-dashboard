import re
import sys
import subprocess
import textwrap
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

runbook_path = Path("reports/phase7_step4_predeployment_runbook.md")
content = runbook_path.read_text(encoding="utf-8")

# Extract all ```bash ... ``` code blocks
pattern = re.compile(r"```bash\n(.*?)```", re.DOTALL)
matches = list(pattern.finditer(content))
print(f"Found {len(matches)} bash code blocks in runbook.")

bash_executable = r"C:\Program Files\Git\bin\bash.exe"
failed_count = 0

for idx, match in enumerate(matches, 1):
    raw_code = match.group(1)
    # Replace placeholders like <SERVER_PUBLIC_IP> with valid dummy values for bash syntax checking
    code_for_syntax = re.sub(r"<[A-Z0-9_]+>", "placeholder_value", raw_code)
    code_for_syntax = textwrap.dedent(code_for_syntax)
    
    line_no = content[:match.start()].count("\n") + 1
    
    result = subprocess.run(
        [bash_executable, "-n"],
        input=code_for_syntax,
        text=True,
        encoding="utf-8",
        capture_output=True
    )
    
    if result.returncode != 0:
        failed_count += 1
        print(f"[FAIL] Block #{idx} at line {line_no}: syntax error!")
        print(result.stderr.strip())

if failed_count == 0:
    print(f"[SUCCESS] All {len(matches)} bash code blocks passed 'bash -n' syntax verification perfectly!")
else:
    print(f"[FAIL] Total {failed_count} block(s) failed syntax validation.")
    sys.exit(1)
