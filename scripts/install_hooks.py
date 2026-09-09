#!/usr/bin/env python3
"""Git-Fix Hook Installation Script.

Sets up the pre-commit hook template for the Git-Fix project.
Copies hooks to the git template directory and makes them executable.
"""

import os
import shutil
import sys
from pathlib import Path


def install_hooks():
    """Install Git-Fix pre-commit hooks."""
    project_dir = Path(__file__).parent.parent.parent.parent.parent if '__file__' in dir() else Path.cwd()
    
    # Determine project directory - go up from the script location
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1]).resolve()
    else:
        # Try to find project root
        for potential in [Path.cwd(), Path.cwd().parent, Path.cwd().parent.parent]:
            if (potential / "backend").exists() and (potential / "README.md").exists():
                project_dir = potential
                break
    
    hooks_dir = project_dir / "backend" / "hooks"
    git_template_dir = Path.home() / ".git-templates" / "git-fix-hooks"
    
    print(f"🔧 Git-Fix Hook Installation")
    print(f"   Project directory: {project_dir}")
    print(f"   Hooks source: {hooks_dir}")
    print(f"   Git template target: {git_template_dir}")
    
    # Create git template directory
    git_template_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy hook scripts
    for hook_file in hooks_dir.glob("*.py"):
        target = git_template_dir / hook_file.name
        shutil.copy2(hook_file, target)
        os.chmod(target, 0o755)
        print(f"   ✅ Installed: {hook_file.name}")
    
    # Configure git to use the template
    git_dir = project_dir / ".git"
    if git_dir.exists():
        # Set git config for template directory
        try:
            subprocess.run(
                ["git", "config", "--local", "init.templateDir", str(git_template_dir)],
                capture_output=True, check=True
            )
            print(f"   ✅ Git template configured")
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️ Could not set template dir: {e}")
    
    # Also copy to core template if user approves
    print(f"\n📋 To use these hooks:")
    print(f"   1. Initialize a new repo: git init")
    print(f"   2. Hooks will auto-install from template")
    print(f"   3. Or copy manually: cp {git_template_dir}/*.py .git/hooks/")
    
    return True


if __name__ == "__main__":
    success = install_hooks()
    sys.exit(0 if success else 1)