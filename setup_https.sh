#!/bin/bash

# Setup HTTPS for Navigation App
# This will enable SSL/TLS and make camera access work

echo "═══════════════════════════════════════════════════════════"
echo "🔒 HTTPS Setup for Navigation App"
echo "═══════════════════════════════════════════════════════════"
echo ""

cat << 'EOF'

You have 2 OPTIONS to enable HTTPS:

═══════════════════════════════════════════════════════════════
OPTION 1: Self-Signed Certificate (Quick Testing) ⚡
═══════════════════════════════════════════════════════════════

This creates a temporary SSL certificate for testing.
Browser will show a security warning (you'll need to click "Advanced" → "Proceed").

Run these commands on your production server:

ssh root@64.23.234.72

# Step 1: Create SSL directory
mkdir -p /etc/ssl/navigation
cd /etc/ssl/navigation

# Step 2: Generate self-signed certificate (valid for 1 year)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem \
  -out cert.pem \
  -subj "/C=AE/ST=AbuDhabi/L=AbuDhabi/O=Navigation/CN=64.23.234.72"

# Step 3: Install gunicorn for production HTTPS
cd /var/www/navigation2
source venv/bin/activate
pip install gunicorn

# Step 4: Create startup script with SSL
cat > /var/www/navigation2/start_https.sh << 'STARTSCRIPT'
#!/bin/bash
cd /var/www/navigation2
source venv/bin/activate
gunicorn --certfile=/etc/ssl/navigation/cert.pem \
         --keyfile=/etc/ssl/navigation/key.pem \
         --bind 0.0.0.0:5001 \
         --workers 2 \
         --timeout 120 \
         --access-logfile app_access.log \
         --error-logfile app_error.log \
         app:app
STARTSCRIPT

chmod +x /var/www/navigation2/start_https.sh

# Step 5: Stop old Flask process and start with SSL
pkill -f 'python app.py'
pkill -f 'gunicorn'
sleep 2

nohup /var/www/navigation2/start_https.sh > /dev/null 2>&1 &

# Step 6: Verify it's running
sleep 3
ps aux | grep gunicorn
curl -k https://localhost:5001/google | head -10

echo ""
echo "✅ HTTPS enabled!"
echo "🌐 Access at: https://64.23.234.72:5001/google"
echo "⚠️  You'll see a security warning - click 'Advanced' then 'Proceed'"
echo ""


═══════════════════════════════════════════════════════════════
OPTION 2: Domain + Let's Encrypt (Production-Ready) 🌟
═══════════════════════════════════════════════════════════════

This requires a domain name pointing to your server.
Provides a real, trusted SSL certificate.

Prerequisites:
- Domain name (e.g., navigation.yourdomain.com)
- Domain's DNS A record points to 64.23.234.72

Steps:

ssh root@64.23.234.72

# Step 1: Install Nginx and Certbot
apt update
apt install -y nginx certbot python3-certbot-nginx

# Step 2: Configure Nginx
cat > /etc/nginx/sites-available/navigation << 'NGINX'
server {
    listen 80;
    server_name navigation.yourdomain.com;  # REPLACE WITH YOUR DOMAIN
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

# Step 3: Enable site
ln -s /etc/nginx/sites-available/navigation /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default  # Remove default site
nginx -t
systemctl restart nginx

# Step 4: Get SSL certificate from Let's Encrypt (FREE)
certbot --nginx -d navigation.yourdomain.com --non-interactive --agree-tos -m your@email.com

# Step 5: Ensure Flask app runs on localhost only
cd /var/www/navigation2
pkill -f 'python app.py'
source venv/bin/activate
nohup python app.py runserver 127.0.0.1:5001 > app.log 2>&1 &

# Step 6: Test
curl https://navigation.yourdomain.com/google | head -10

echo ""
echo "✅ Production HTTPS enabled!"
echo "🌐 Access at: https://navigation.yourdomain.com/google"
echo "🎥 Camera will work!"
echo ""


═══════════════════════════════════════════════════════════════
OPTION 3: SSH Tunnel (Testing Camera Locally) 🧪
═══════════════════════════════════════════════════════════════

Use SSH tunnel to test camera without SSL setup:

# On your local machine, run:
ssh -N -L 5001:localhost:5001 root@64.23.234.72

# Then open in your browser:
http://localhost:5001/google

# Camera will work because browser sees it as "localhost"!


═══════════════════════════════════════════════════════════════
RECOMMENDED CHOICE:
═══════════════════════════════════════════════════════════════

For Testing:     Use OPTION 1 (Self-Signed) or OPTION 3 (SSH Tunnel)
For Production:  Use OPTION 2 (Domain + Let's Encrypt)


EOF

echo ""
echo "📋 Which option do you want to use?"
echo ""
echo "1️⃣  Self-Signed Certificate (Quick, shows browser warning)"
echo "2️⃣  Domain + Let's Encrypt (Proper, requires domain name)"  
echo "3️⃣  SSH Tunnel (Testing only)"
echo ""


