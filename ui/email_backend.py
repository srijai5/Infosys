# ui/email_backend.py
import ssl
import smtplib
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

class CustomEmailBackend(SMTPBackend):
    def open(self):
        if self.connection:
            return False
        
        try:
            # Disable SSL certificate verification
            self.connection = smtplib.SMTP(self.host, self.port)
            self.connection.ehlo()
            
            if self.use_tls:
                # Create unverified SSL context
                context = ssl._create_unverified_context()
                self.connection.starttls(context=context)
                
            self.connection.ehlo()
            
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise
            return False