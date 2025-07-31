# Step 1: Clone and go to backend dir
git clone https://github.com/your-username/legal-risk-app.git
cd legal-risk-app/backend

# Step 2: Setup venv and activate (Windows example)
python -m venv venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# PowerShell
.\venv\Scripts\Activate.ps1
# or Command Prompt
venv\Scripts\activate
# or Bash/Linux/Mac
source venv/bin/activate


# Step 3: Install requirements
pip install -r requirements.txt

# Step 4: Run your backend
python app.py
