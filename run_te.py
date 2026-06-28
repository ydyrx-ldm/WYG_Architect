import subprocess, sys, os
os.chdir(r"c:\yaoge.wang\AI\Agent\WYG\mcp-chinese-dict")
r = subprocess.run([sys.executable, "debug2.py"], capture_output=True)
with open("debug2_out.txt", "wb") as f:
    f.write(r.stdout)
    f.write(b"\n--- STDERR ---\n")
    f.write(r.stderr)
print("done, rc=", r.returncode)
