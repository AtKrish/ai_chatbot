Quickest Fix (start fresh Git history)
Since this looks like a personal project, the easiest approach is:

# Delete existing git history
Remove-Item -Recurse -Force .git

# Reinitialize repository
git init

# Create .gitignore
New-Item .gitignore
Put this in .gitignore:

venv/
venv311/
.venv/

__pycache__/
*.pyc

.env

.vscode/

*.log
Then:

git add .
git commit -m "Initial commit"

git branch -M main

git remote add origin https://github.com/AtKrish/ai_chatbot.git

git push -u origin main --force
Before pushing, verify venv is excluded
Run:

git status
You should NOT see:

venv/
venv311/
in the staged files.

Also check:

git add .
git status
You should only see folders like:

backend/
frontend/
models/
services/
utils/
data/
requirements.txt
README.md
and not thousands of files from site-packages.

If you don't want to delete Git history
Use:

git rm -r --cached venv
git rm -r --cached venv311
Then install git-filter-repo and remove those folders from all commits. But for a local project that hasn't been successfully pushed yet, deleting .git and reinitializing is usually much faster and cleaner.
