"""
Lab challenge catalog — static definitions.
Each challenge maps to a Docker container and a set of flags to find.
"""
import hashlib

def _h(flag_text: str) -> str:
    """SHA-256 hash of a flag string."""
    return hashlib.sha256(flag_text.encode()).hexdigest()


CHALLENGES: dict = {
    "dvwa": {
        "name": "DVWA",
        "description": (
            "Damn Vulnerable Web Application — classic OWASP Top 10 training ground. "
            "Practice SQL injection, XSS, CSRF, file inclusion, command execution, and more."
        ),
        "image": "vulnerables/web-dvwa:latest",
        "container_name": "lab-dvwa",
        "host_port": 8081,
        "container_port": 80,
        "network_ip": "172.30.0.10",
        "category": "Web",
        "difficulty": "Beginner",
        "points_total": 500,
        "flags": {
            "sqli": {
                "name": "SQL Injection",
                "description": "Dump the users table via SQL injection on the User ID field.",
                "points": 100,
                "hash": _h("DVWA{sqli_admin_password_dumped}"),
                "flag": "DVWA{sqli_admin_password_dumped}",
                "hints": [
                    "Try entering a single quote ' in the User ID field.",
                    "Use UNION SELECT to dump data from other tables.",
                    "The users table has columns: user, password.",
                ],
            },
            "xss_r": {
                "name": "Reflected XSS",
                "description": "Trigger an alert() via reflected XSS in the name parameter.",
                "points": 75,
                "hash": _h("DVWA{xss_reflected_alert}"),
                "flag": "DVWA{xss_reflected_alert}",
                "hints": [
                    "Look for input fields that echo your input back.",
                    "Try <script>alert(1)</script>.",
                    "If filtered, try event handlers like onerror=alert(1).",
                ],
            },
            "xss_s": {
                "name": "Stored XSS",
                "description": "Inject a persistent XSS payload into the guestbook.",
                "points": 100,
                "hash": _h("DVWA{xss_stored_guestbook}"),
                "flag": "DVWA{xss_stored_guestbook}",
                "hints": [
                    "The guestbook saves your message to the database.",
                    "Every visitor who views the page will execute your script.",
                ],
            },
            "cmdi": {
                "name": "Command Injection",
                "description": "Execute arbitrary OS commands via the ping utility.",
                "points": 125,
                "hash": _h("DVWA{cmdi_rce_whoami}"),
                "flag": "DVWA{cmdi_rce_whoami}",
                "hints": [
                    "The ping field passes your input to the OS.",
                    "Try appending a second command with ; or &&.",
                    "Run whoami to confirm code execution.",
                ],
            },
            "lfi": {
                "name": "File Inclusion",
                "description": "Read /etc/passwd via Local File Inclusion.",
                "points": 100,
                "hash": _h("DVWA{lfi_etc_passwd}"),
                "flag": "DVWA{lfi_etc_passwd}",
                "hints": [
                    "Look for page= or file= URL parameters.",
                    "Try ../../etc/passwd as the value.",
                    "Use ../ sequences to traverse directories.",
                ],
            },
        },
    },

    "juice": {
        "name": "OWASP Juice Shop",
        "description": (
            "Modern intentionally vulnerable web shop. Covers XSS, SQLi, broken access "
            "control, JWT forgery, API abuse, and 100+ unique challenges."
        ),
        "image": "bkimminich/juice-shop:latest",
        "container_name": "lab-juice",
        "host_port": 3001,
        "container_port": 3000,
        "network_ip": "172.30.0.11",
        "category": "Web / API",
        "difficulty": "Intermediate",
        "points_total": 600,
        "flags": {
            "login_admin": {
                "name": "Admin Login",
                "description": "Log in as the administrator without knowing the password.",
                "points": 100,
                "hash": _h("JUICE{admin_login_bypass}"),
                "flag": "JUICE{admin_login_bypass}",
                "hints": [
                    "The login uses SQL under the hood.",
                    "Classic ' OR 1=1-- works on many forms.",
                    "The admin email is admin@juice-sh.op.",
                ],
            },
            "jwt_forge": {
                "name": "JWT Forgery",
                "description": "Forge a JWT token to escalate to admin privileges.",
                "points": 200,
                "hash": _h("JUICE{jwt_none_algorithm}"),
                "flag": "JUICE{jwt_none_algorithm}",
                "hints": [
                    "Decode your JWT — what algorithm does it use?",
                    "Try changing the algorithm to 'none'.",
                    "Remove the signature and set isAdmin: true in the payload.",
                ],
            },
            "path_traversal": {
                "name": "Path Traversal",
                "description": "Access the /ftp directory to download a restricted file.",
                "points": 150,
                "hash": _h("JUICE{path_traversal_ftp}"),
                "flag": "JUICE{path_traversal_ftp}",
                "hints": [
                    "Try browsing to /ftp in the app.",
                    "Some files are blocked — use null byte or encoding tricks.",
                ],
            },
            "sqli_raw": {
                "name": "Raw SQL Query",
                "description": "Exfiltrate customer data via the search bar.",
                "points": 150,
                "hash": _h("JUICE{sqli_search_exfil}"),
                "flag": "JUICE{sqli_search_exfil}",
                "hints": [
                    "The search feature queries the database directly.",
                    "Close the query and append UNION SELECT.",
                ],
            },
        },
    },

    "webgoat": {
        "name": "WebGoat",
        "description": (
            "OWASP WebGoat is a deliberately insecure web application designed for teaching "
            "web application security lessons with guided tutorials."
        ),
        "image": "webgoat/webgoat:latest",
        "container_name": "lab-webgoat",
        "host_port": 8083,
        "container_port": 8080,
        "network_ip": "172.30.0.13",
        "category": "Web / Guided",
        "difficulty": "Beginner",
        "points_total": 300,
        "flags": {
            "idor": {
                "name": "IDOR",
                "description": "Access another user's account data via Insecure Direct Object Reference.",
                "points": 150,
                "hash": _h("WEBGOAT{idor_other_profile}"),
                "flag": "WEBGOAT{idor_other_profile}",
                "hints": [
                    "Find a request that uses a numeric user ID.",
                    "Change the ID to access another user's profile.",
                ],
            },
            "xxe": {
                "name": "XXE Injection",
                "description": "Read /etc/passwd via XML External Entity injection.",
                "points": 150,
                "hash": _h("WEBGOAT{xxe_etc_passwd}"),
                "flag": "WEBGOAT{xxe_etc_passwd}",
                "hints": [
                    "Find an endpoint that accepts XML input.",
                    "Define an external entity that reads a local file.",
                    "<!ENTITY xxe SYSTEM 'file:///etc/passwd'>",
                ],
            },
        },
    },

    "metasploitable": {
        "name": "Metasploitable 2",
        "description": (
            "Ubuntu 8.04 VM intentionally configured with dozens of vulnerable network "
            "services. Practice Metasploit modules, manual exploitation, privilege escalation."
        ),
        "image": "tleemcjr/metasploitable2:latest",
        "container_name": "lab-metasploitable",
        "host_port": 8084,
        "container_port": 80,
        "network_ip": "172.30.0.14",
        "category": "Network / Services",
        "difficulty": "Intermediate",
        "points_total": 700,
        "flags": {
            "ftp_backdoor": {
                "name": "vsftpd 2.3.4 Backdoor",
                "description": "Exploit the vsftpd backdoor to get a root shell.",
                "points": 200,
                "hash": _h("META{vsftpd_root_shell}"),
                "flag": "META{vsftpd_root_shell}",
                "hints": [
                    "vsftpd 2.3.4 has a famous backdoor triggered by :) in the username.",
                    "Metasploit module: exploit/unix/ftp/vsftpd_234_backdoor",
                    "The backdoor opens a shell on port 6200.",
                ],
            },
            "samba_rce": {
                "name": "Samba usermap_script",
                "description": "Exploit the Samba usermap_script vulnerability for RCE.",
                "points": 200,
                "hash": _h("META{samba_rce_root}"),
                "flag": "META{samba_rce_root}",
                "hints": [
                    "Samba 3.0.20 has CVE-2007-2447.",
                    "Metasploit: exploit/multi/samba/usermap_script",
                ],
            },
            "postgres_rce": {
                "name": "PostgreSQL RCE",
                "description": "Use default PostgreSQL credentials to execute OS commands.",
                "points": 150,
                "hash": _h("META{postgres_rce_id}"),
                "flag": "META{postgres_rce_id}",
                "hints": [
                    "Default creds: postgres/postgres.",
                    "Metasploit: exploit/linux/postgres/postgres_payload",
                ],
            },
            "priv_esc": {
                "name": "Local Privilege Escalation",
                "description": "Escalate from a low-privilege shell to root.",
                "points": 150,
                "hash": _h("META{privesc_root_flag}"),
                "flag": "META{privesc_root_flag}",
                "hints": [
                    "Check SUID binaries: find / -perm -4000 2>/dev/null",
                    "Look at sudo -l for misconfigured permissions.",
                ],
            },
        },
    },

    "bwapp": {
        "name": "bWAPP",
        "description": (
            "Buggy Web Application — over 100 web vulnerabilities across all OWASP categories. "
            "Great for practicing both basic and advanced web attacks."
        ),
        "image": "raesene/bwapp:latest",
        "container_name": "lab-bwapp",
        "host_port": 8082,
        "container_port": 80,
        "network_ip": "172.30.0.12",
        "category": "Web",
        "difficulty": "Intermediate",
        "points_total": 400,
        "flags": {
            "html_inject": {
                "name": "HTML Injection",
                "description": "Inject arbitrary HTML into the page via a GET parameter.",
                "points": 75,
                "hash": _h("BWAPP{html_inject_get}"),
                "flag": "BWAPP{html_inject_get}",
                "hints": [
                    "Find a page that reflects a query parameter.",
                    "Try injecting <h1>test</h1>.",
                ],
            },
            "ssrf": {
                "name": "Server-Side Request Forgery",
                "description": "Make the server fetch an internal resource via SSRF.",
                "points": 175,
                "hash": _h("BWAPP{ssrf_internal_request}"),
                "flag": "BWAPP{ssrf_internal_request}",
                "hints": [
                    "Look for features that load remote URLs.",
                    "Try pointing it at http://127.0.0.1/.",
                ],
            },
            "xxe_bwapp": {
                "name": "XXE",
                "description": "Extract /etc/passwd via XML External Entity injection.",
                "points": 150,
                "hash": _h("BWAPP{xxe_file_read}"),
                "flag": "BWAPP{xxe_file_read}",
                "hints": [
                    "Find an XML input field.",
                    "Inject a DOCTYPE with an external entity.",
                ],
            },
        },
    },
}
