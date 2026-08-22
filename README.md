# Setup Steps
1. Project Setup->
Open the project directory in VS Code.

2. Create a GitHub repository->
Upload the folder on Github repo

3. Create Python virtual environment

4. Install dependencies->
Installing the required Python packages using requirements.txt

5. Install FFmpeg->
The audio task requires FFmpeg

6. Run the data pipeline->
Source records loaded: 103
Unique people: 60
Potentially merged records: 43
Data issues captured: 52
Report: data/data_issues_report.csv

7. Inspect the database->
sqlite3 database/consultbae.db

8. Run the Flask Application
Start the Flask application using app/app.py to open the audio collection interface.

9. Set Up n8n->
Create/sign into your workspace and open the duplicate-alert workflow in the project folder.

10. Set Up ngrok->
Using ngrok to expose the local application through an HTTPS URL when required for webhook communication.

11. Configure Duplicate Alert Workflow->
Configure the n8n workflow to receive the required data and identify whether the record is a duplicate. When the duplicate result is true, the workflow sends an email alert.

12. Verify Email Notification->
Confirm that the n8n workflow successfully sends the duplicate alert email.



# Data Issues Reprt
1. Inconsistent Data Formats->
Some fields were not represented consistently across the input data.Before processing, I normalized the relevant fields so that records could be compared more reliably.

2. Duplicate and Near-Duplicate Records->
Some records represented the same or very similar entities but were not necessarily identical at the raw-data level. Exact string comparison alone would therefore not always be sufficient. I used normalization and entity-resolution logic to improve the identification of duplicate or matching records.

3. Inconsistent Text Values->
Some textual fields contained differences such as:
Different capitalization,
Extra whitespace,
Formatting differences,
Slight variations in how the same value was written

4. Missing or Incomplete Values->
Some records contained missing or incomplete values. Instead of assuming that a missing value represented a particular value, I preserved the missing state where appropriate and handled it during processing.



# Stuck Log

`Gmail SMTP Authentication`:
1. Problem->
While implementing the email notification part of the pipeline, I initially received the following Gmail SMTP error: 535-5.7.8 Username and Password not accepted

2. Searching->
Gmail SMTP 535 5.7.8 Username and Password not accepted
Checked Google's guidance related to Gmail SMTP authentication and App Passwords

3. Asking AI-> 
Everything is correct I have given 16 character app password so why is it not working

4. Getting Unstuck-> 
I deleted the the old App Password and created a new one and it successfully worked

`Working with n8n`
1. Problem->
Making the workflow work such that all the nodes work and the email got send upon true
Integrating n8n with ngrok 

2. Searching->
How to connect localhost to n8n using ngrok
How the nodes work 

3. Asking AI->
Data passing through the nodes 
Why the webhook node should be in starting 

4. Getting Unstuck->
Changed the URL in Check SQLite via api with ngrok forwarding URL
 










