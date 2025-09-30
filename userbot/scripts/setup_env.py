#!/usr/bin/env python3
"""
Setup script untuk membuat virtual environment dan install dependencies.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

class EnvironmentSetup:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.venv_dir = self.project_dir / "venv"
        
    def setup_environment(self):
        """Setup virtual environment dan install dependencies."""
        print("🔧 SETTING UP PYTHON VIRTUAL ENVIRONMENT")
        print("=" * 50)
        
        # 1. Check Python version
        python_version = sys.version_info
        print(f"✅ Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        if python_version < (3, 8):
            print("❌ Python 3.8+ required!")
            return False
            
        # 2. Remove existing venv if exists
        if self.venv_dir.exists():
            print(f"🗑️ Removing existing venv: {self.venv_dir}")
            shutil.rmtree(self.venv_dir)
            
        # 3. Create new virtual environment
        print(f"🏗️ Creating virtual environment: {self.venv_dir}")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_dir)], 
                          check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create venv: {e}")
            return False
            
        # 4. Get venv python and pip paths
        if os.name == 'nt':  # Windows
            venv_python = self.venv_dir / "Scripts" / "python.exe"
            venv_pip = self.venv_dir / "Scripts" / "pip.exe"
        else:  # Linux/macOS
            venv_python = self.venv_dir / "bin" / "python"
            venv_pip = self.venv_dir / "bin" / "pip"
            
        # 5. Upgrade pip in venv
        print("📦 Upgrading pip in virtual environment...")
        try:
            subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], 
                          check=True)
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Failed to upgrade pip: {e}")
            
        # 6. Install requirements
        requirements_file = self.project_dir / "requirements.txt"
        if requirements_file.exists():
            print("📦 Installing dependencies from requirements.txt...")
            try:
                subprocess.run([str(venv_pip), "install", "-r", str(requirements_file)], 
                              check=True)
                print("✅ Dependencies installed successfully!")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install requirements: {e}")
                return False
        else:
            print("⚠️ requirements.txt not found")
            
        # 7. Create activation script
        self.create_activation_script()
        
        # 8. Test installation
        self.test_installation(venv_python)
        
        print("\n" + "="*50)
        print("🎯 VIRTUAL ENVIRONMENT SETUP COMPLETE!")
        print(f"📁 Location: {self.venv_dir}")
        print("\n🚀 TO ACTIVATE:")
        if os.name == 'nt':
            print(f"   .\\venv\\Scripts\\activate")
        else:
            print(f"   source venv/bin/activate")
        print("\n📜 OR USE ACTIVATION SCRIPT:")
        print("   python3 activate_env.py")
        print("="*50)
        
        return True
        
    def create_activation_script(self):
        """Create convenience activation script."""
        activation_script = '''#!/usr/bin/env python3
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
            print("\\n🚀 To activate manually:")
            print("   .\\\\venv\\\\Scripts\\\\activate")
        else:
            print("\\n🚀 To activate manually:")
            print("   source venv/bin/activate")
            
        print("\\n📜 To run commands in venv:")
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
'''
        
        script_path = self.project_dir / "activate_env.py"
        with open(script_path, 'w') as f:
            f.write(activation_script)
            
        os.chmod(script_path, 0o755)
        print(f"✅ Activation script created: {script_path}")
        
    def test_installation(self, venv_python):
        """Test key dependencies."""
        print("\n🧪 Testing key dependencies...")
        
        test_imports = [
            "telethon",
            "psycopg2", 
            "cryptography",
            "dotenv",
            "httpx"
        ]
        
        for module in test_imports:
            try:
                result = subprocess.run([str(venv_python), "-c", f"import {module}; print(f'✅ {module} imported successfully')"], 
                                      capture_output=True, text=True, check=True)
                print(result.stdout.strip())
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to import {module}: {e}")

def main():
    """Main setup function."""
    setup = EnvironmentSetup()
    success = setup.setup_environment()
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("\n🚀 Next steps:")
        print("1. python3 activate_env.py tests/admin_reply_guard_test.py")
        print("2. python3 activate_env.py tests/comprehensive_debug_fix.py")
        print("3. python3 activate_env.py userbot/main.py --owner-id 5473468582")
    else:
        print("\n❌ Setup failed! Check errors above.")
        
if __name__ == "__main__":
    main()