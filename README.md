# Network-Health-Check
# Network Health Report Tool

This script automates the collection and reporting of network switch health data for Cisco IOS devices. It performs the following checks:

## Features

* ✅ Detects err-disabled interfaces
* 🔌 Monitors power supply issues
* 🛡️ Parses DHCP snooping log messages (only from the current month)
* ⚙️ Flags sustained high CPU usage (>60% over 5-minute average)
* 🌡️ Checks for high inlet temperatures (>100°F)
* 📡 Validates Access Point (AP) naming from CDP neighbors against a naming pattern
* 📨 Sends a full HTML email report to specified recipients

---

## Requirements

* Python 3.6+
* Cisco IOS switches with SSH access

### Python Packages

```bash
pip install netmiko jinja2
```

---

## Usage

1. **Create `accessswitches.txt`**

   * Place the IP addresses of your switches in this file, one per line:

```
10.1.1.1
10.1.1.2
10.1.1.3
```

2. **Run the script**

```bash
python3 network_health_report.py
```

3. **When prompted**, enter SSH username and password.

4. **Email report** will be sent to the configured recipient (`mike@fau.edu`) via `smtp.fau.edu`.

---

## AP Naming Check Logic

* The script looks for CDP neighbors where the device ID starts with `AP`
* Valid AP names follow the pattern: `AP-XYZ123` (customizable)
* If invalid, it reports:

  * Device ID
  * Local port (interface)
  * Interface description (if configured)

---

## Sample Output (in email)

```
Switch01 (10.1.1.1)
📡 Improperly named Access Points detected:
 - AP1234 on Gi1/0/2 — Uplink AP without proper name
⛔ Err-disabled interfaces detected:
 - Gi1/0/3 err-disabled
🌡️ High inlet temperature: 105.2°F (40.7°C)
```

---

## Customization Ideas

* Export to local HTML or CSV file
* Integration with ticketing systems (e.g. ServiceNow API)
* Add remediation for common issues (e.g., shut/no shut)

---

## License

MIT License - free to use and modify.

---

## Contact

Created by the FAU Networking Team.
For questions or feature requests, contact: `mike@fau.edu`
