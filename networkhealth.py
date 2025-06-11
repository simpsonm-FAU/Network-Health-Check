import getpass
import re
from datetime import datetime
from netmiko import ConnectHandler
from jinja2 import Template
from email.mime.text import MIMEText
import smtplib

# --- Access Point validation helper ---
def extract_bad_ap_names(cdp_text, ifdesc_text):
    bad_aps = []
    ifdesc_map = {}

    # Build interface description map
    for line in ifdesc_text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            intf = parts[0]
            desc = " ".join(parts[1:])
            ifdesc_map[intf] = desc

    current_ap = None
    current_port = None

    for line in cdp_text.splitlines():
        line = line.strip()
        if line.lower().startswith("device id:"):
            current_ap = line.split("Device ID:")[1].strip()
        elif line.lower().startswith("interface:"):
            match = re.search(r'Interface: ([^,]+)', line)
            if match:
                current_port = match.group(1)
        elif current_ap and current_port:
            if current_ap.startswith("AP") and not re.match(r"^AP-[\w\d\-]+$", current_ap):
                desc = ifdesc_map.get(current_port, "(no description)")
                bad_aps.append(f"{current_ap} on {current_port} — {desc}")
            current_ap = None
            current_port = None

    return bad_aps

# --- Analyzer ---
def analyze_all(err_text, power_text, dhcp_log_text, cpu_text, temp_text, cdp_text, ifdesc_text):
    issues = []

    # Err-disabled interfaces
    if "err-disabled" in err_text.lower():
        interfaces = [line.strip() for line in err_text.splitlines() if "err-disabled" in line.lower()]
        if interfaces:
            issues.append("⛔ Err-disabled interfaces detected:")
            issues.extend([f"&nbsp;&nbsp;- {i}" for i in interfaces])

    # Power supply issues
    for line in power_text.splitlines():
        if any(x in line.lower() for x in ["not present", "fail", "off", "bad", "shutdown"]):
            issues.append("🔌 Power supply issue: " + line.strip())

    # DHCP snooping logs (current month only)
    current_month = datetime.now().strftime("%b")
    dhcp_messages = [
        line.strip() for line in dhcp_log_text.splitlines()
        if "dhcp_snooping" in line.lower() and line.strip().startswith(current_month)
    ]
    if dhcp_messages:
        issues.append("🛡️ DHCP Snooping messages (this month):")
        issues.extend([f"&nbsp;&nbsp;- {m}" for m in dhcp_messages])

    # CPU check (5-minute avg > 60%)
    match = re.search(r'five minutes: (\d+)%', cpu_text)
    if match:
        cpu_5min = int(match.group(1))
        if cpu_5min > 60:
            issues.append(f"⚙️ Sustained high CPU load: {cpu_5min}% (5 min avg)")

    # Temperature check (Inlet sensors only > 100°F)
    for line in temp_text.splitlines():
        if "inlet" in line.lower():
            parts = line.strip().split()
            for part in parts:
                try:
                    temp_c = float(part)
                    temp_f = (temp_c * 9/5) + 32
                    if temp_f > 100:
                        issues.append(f"🌡️ High inlet temperature: {temp_f:.1f}°F ({temp_c:.1f}°C) on line: {line.strip()}")
                except ValueError:
                    continue

    # Access Point name check
    bad_aps = extract_bad_ap_names(cdp_text, ifdesc_text)
    if bad_aps:
        issues.append("📡 Improperly named Access Points detected:")
        issues.extend([f"&nbsp;&nbsp;- {b}" for b in bad_aps])

    if not issues:
        issues.append("✅ No critical issues detected.")
    return issues

# --- Prompt for credentials ---
ssh_user = input("Enter SSH username: ")
ssh_pass = getpass.getpass("Enter SSH password: ")

# --- Read switch IPs ---
with open("accessswitches.txt") as f:
    switch_ips = [line.strip() for line in f if line.strip()]

# --- Collect results ---
all_results = []

for ip in switch_ips:
    print(f"Connecting to {ip}...")
    device = {
        'device_type': 'cisco_ios',
        'host': ip,
        'username': ssh_user,
        'password': ssh_pass,
    }

    try:
        conn = ConnectHandler(**device)

        errdisable_output = conn.send_command("show interfaces status err-disabled")
        power_output = conn.send_command("show environment power")
        dhcp_logs_output = conn.send_command("show logging | include DHCP_SNOOPING")
        cpu_output = conn.send_command("show processes cpu | include five minutes")
        temp_output = conn.send_command("show environment temperature")
        cdp_output = conn.send_command("show cdp neighbors detail")
        ifdesc_output = conn.send_command("show interfaces description")
        hostname = conn.find_prompt().strip("#")

        conn.disconnect()

        issues = analyze_all(
            errdisable_output,
            power_output,
            dhcp_logs_output,
            cpu_output,
            temp_output,
            cdp_output,
            ifdesc_output
        )

        all_results.append({"hostname": hostname, "ip": ip, "issues": issues})

    except Exception as e:
        all_results.append({"hostname": ip, "ip": ip, "issues": [f"❌ Failed to connect: {str(e)}"]})

# --- Generate report ---
def generate_full_report(results):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    template = Template("""
    <h2>Network Health Report</h2>
    <p><strong>Generated:</strong> {{ timestamp }}</p>
    {% for item in results %}
        <h3>{{ item.hostname }} ({{ item.ip }})</h3>
        <ul>
        {% for issue in item.issues %}
            <li>{{ issue|safe }}</li>
        {% endfor %}
        </ul>
    {% endfor %}
    """)
    return template.render(results=results, timestamp=now)

html_report = generate_full_report(all_results)

# --- Send the email ---
sender = "network-report@youremail.com"
recipient = "yourname@youremail.com"
subject = "Multi-Switch Network Health Report"

msg = MIMEText(html_report, "html")
msg["Subject"] = subject
msg["From"] = sender
msg["To"] = recipient

try:
    print("Sending email...")
    with smtplib.SMTP("smtp.youremailserver.com", 25, timeout=10) as server:
        server.send_message(msg)
    print("✅ Email sent successfully.")
except Exception as e:
    print(f"❌ Failed to send email: {e}")
