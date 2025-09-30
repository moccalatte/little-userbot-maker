#!/usr/bin/env python3
"""
Convenience script untuk aktivasi virtual environment.
"""
import os
import sys
import subprocess
from pathlib import Path

def activate_and_run(command=None):
    """Activate venv dan run command jika diberikan."""
    project_dir = Path(__file__).parent
    
    if os.name == 'nt':  # Windows
        activate_script = project_dir / "venv" / "Scripts" / "activate.bat"
        python_exe = project_dir / "venv" / "Scripts" / "python.exe"
    else:  # Linux/macOS
        activate_script = project_dir / "venv" / "bin" / "activate"
        python_exe = project_dir / "venv" / "bin" / "python"
        
    if not python_exe.exists():
        print("❌ Virtual environment not found!")
        print("Run: python3 setup_env.py")
        return False
        
    if command:
        # Run command in venv
        if isinstance(command, str):
            command = command.split()
            
        # Prepend venv python to command
        if command[0] == 'python' or command[0] == 'python3':
            command[0] = str(python_exe)
        else:
            command = [str(python_exe)] + command
            
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {e}")
            return False
    else:
        # Just show activation info
        print("🐍 VIRTUAL ENVIRONMENT INFO")
        print("=" * 40)
        print(f"📁 Location: {project_dir / 'venv'}")
        print(f"🐍 Python: {python_exe}")
        
        if os.name == 'nt':
            print("\n🚀 To activate manually:")
            print("   .\\venv\\Scripts\\activate")
        else:
            print("\n🚀 To activate manually:")
            print("   source venv/bin/activate")
            
        print("\n📜 To run commands in venv:")
        print("   python3 activate_env.py <command>")
        print("   Example: python3 activate_env.py python tests/admin_reply_guard_test.py")
        
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run command in venv
        command = sys.argv[1:]
        activate_and_run(command)
    else:
        # Show info
        activate_and_run()
