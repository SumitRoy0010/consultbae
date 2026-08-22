#Stuck Log

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

2. Searching
How to connect localhost to n8n using ngrok
How the nodes work 

3. Asking AI
Data passing through the nodes 
Why the webhook node should be in starting 

4. Getting Unstuck
Changed the URL in Check SQLite via api with ngrok forwarding URL
 










