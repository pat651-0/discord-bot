XSI CONTROL API — PHONE UPLOAD EDITION

Upload only these three files to a new private GitHub repository named:
xsi-control-api

- app.py
- requirements.txt
- railway.json

Do not upload:
- any .pem private key
- .env files
- Discord TOKEN
- GitHub secrets

Then create a new Railway service from that repository.

Required Railway variables:
XSI_CONTROL_ADMIN_KEY
GITHUB_APP_ID
GITHUB_INSTALLATION_ID
GITHUB_PRIVATE_KEY
GITHUB_REPO_OWNER
GITHUB_REPO_NAME
XSI_ALLOWED_ORIGINS=*

The web interface is embedded directly in app.py, so no static folder is required.
