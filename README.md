# HDMI_Matrix_App
A light web app to manage the HDMI and audio output of an OREI HDMI matrix.

Documentation for Matrix: https://cdn.shopify.com/s/files/1/1988/4253/files/UHD-402MV_User_Manual.pdf?v=1693397076

While testing, you need to open the .venv using the following instructions:
1: Open a powershell terminal "CTRL + SHIFT + ` (bactick)".
2: Enter call .\.venv\Scripts\activate
3: When (.venv) is activated, enter python -m uvicorn app:app --host 0.0.0.0 --port 8000
4: Open http://192.168.1.20:8000/ in a browser.
Added this command to run_server.bat. have not tested yet.