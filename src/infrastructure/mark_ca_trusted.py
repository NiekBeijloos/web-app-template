import platform
import subprocess
import argparse
import ctypes

if __name__ == "__main__":
    print("[INFO]: marking TLS CA certificate as 'trusted'")
    parser = argparse.ArgumentParser(description="set CA certificate to be trusted")
    parser.add_argument("path", help="Path to CA certificate file")
    args = parser.parse_args()
    os = platform.system().lower()
    match os:
        case "windows":
            if ctypes.windll.shell32.IsUserAnAdmin() == False:
                raise PermissionError("Make sure to run as Administrator!")
            trust_ca_certificate = f'Import-Certificate -FilePath "{args.path}" -CertStoreLocation Cert:\\LocalMachine\\Root'
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", trust_ca_certificate], check=True, shell=True)
            print(f"[INFO]: marked {args.path} as trusted")
        case _:
            print(f"[INFO]: Non-Windows OS detected. Marking {args.path} as trusted -SKIPPED")