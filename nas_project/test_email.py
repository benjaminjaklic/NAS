import smtplib
from email.mime.text import MIMEText

# Your Gmail credentials
username = 'your.dnas@gmail.com'  # Replace with your exact Gmail address
password = 'ruisgulqddozkofc'     # Replace with your exact App Password

# Recipient email
recipient = 'benjaminjaklic123@gmail.com'  # Use your personal email to test

# Create message
msg = MIMEText('This is a test email from your NAS system.')
msg['Subject'] = 'Test Email from NAS'
msg['From'] = username
msg['To'] = recipient

try:
    # Connect to Gmail's SMTP server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.set_debuglevel(1)  # Enable verbose debug output
    server.ehlo()  # Identify yourself to the server
    server.starttls()  # Secure the connection
    server.ehlo()  # Re-identify yourself over TLS connection
    
    # Attempt to log in
    print(f"Attempting login with username: {username}")
    server.login(username, password)
    
    # Send email
    print("Login successful, sending email...")
    server.sendmail(username, recipient, msg.as_string())
    print("Email sent successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    
finally:
    # Close connection
    try:
        server.quit()
    except:
        pass