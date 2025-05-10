import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import argparse
import requests

class tls_certificate_generator:
    def __init__(self, output_path:Path, ca_cer_path:Path, ca_key_path:Path, ip):
        self.output_path = output_path
        self.ca_cer_path = ca_cer_path
        self.ca_key_path = ca_key_path
        self.ip = ip
        print(f"[INFO]: using IP:{self.ip}, CA_CER_PATH: {self.ca_cer_path}, CA_KEY_PATH: {self.ca_key_path} for certificate generation...")

    def __read_cer(self, cer_path:Path):
        if not cer_path.exists():
            print(f"[ERROR]: unable to read {cer_path} as it does not exist")
            return None
        with open(str(cer_path), "rb") as f:
            cer = x509.load_pem_x509_certificate(f.read())
        return cer
    
    def __read_crt(self, cer_path:Path):
        if not cer_path.exists():
            print(f"[ERROR]: unable to read {cer_path} as it does not exist")
            return None
        with open(str(cer_path), "rb") as f:
            crt = x509.load_pem_x509_csr(f.read())
        return crt
    
    def __read_key(self, key_path:Path):
        if not key_path.exists():
            print(f"[ERROR]: unable to read {key_path} as it does not exist")
            return None
        with open(str(key_path), "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
        return key
    
    def __write_key(self, key, key_output_path:Path):
        with open(str(key_output_path), "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()))
    
    def __write_cer(self, cer, cer_output_path:Path):
        with open(str(cer_output_path), "wb") as f:
            f.write(cer.public_bytes(serialization.Encoding.PEM))
    
    def generate_ca_certificate(self):
        print("[INFO]: generating ca certificate...")
        ca_key = ec.generate_private_key(ec.SECP256R1())
        issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "I'm my own authority")])
        ca_cer = (
            x509.CertificateBuilder()
            .subject_name(issuer)
            .issuer_name(issuer)
            .public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=36500))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(
                digital_signature=False, 
                key_encipherment=False, 
                content_commitment=False, 
                data_encipherment=False, 
                key_agreement=False, 
                key_cert_sign=True, 
                crl_sign=True, 
                encipher_only=False, 
                decipher_only=False
            ), critical=True)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256())
        )

        self.__write_cer(ca_cer, self.ca_cer_path)
        self.__write_key(ca_key, self.ca_key_path)
    
    def __generate_server_certificate_request(self):
        print("[INFO]: generating server certificate request...")
        server_key = ec.generate_private_key(ec.SECP256R1())
        server_certificate_request = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, self.ip)
            ]))
            .sign(server_key, hashes.SHA256())
        )
        self.__write_cer(server_certificate_request, Path(f"{self.output_path}/server.crt"))
        self.__write_key(server_key, Path(f"{self.output_path}/server.key"))
    
    def __sign_server_certificate_request(self, expiration_days):  
        print("[INFO]: singning server certificate request...")
        ca_cer = self.__read_cer(self.ca_cer_path)
        ca_key = self.__read_key(self.ca_key_path)
        server_certificate_request = self.__read_crt(Path(f"{self.output_path}/server.crt"))
        
        server_certificate=(
            x509.CertificateBuilder()
                .subject_name(server_certificate_request.subject)
                .issuer_name(ca_cer.subject)
                .public_key(server_certificate_request.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.now(timezone.utc))
                .not_valid_after(datetime.now(timezone.utc) + timedelta(days=expiration_days))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(self.ip))]), critical=False)
                .sign(ca_key, hashes.SHA256())
        )

        self.__write_cer(server_certificate, Path(f"{self.output_path}/server.cer"))
    
    def generate_server_certificate(self, expiration_days):
        print(f"[INFO]: generating server certificate, will expire in: {expiration_days} days...")
        self.__generate_server_certificate_request()
        self.__sign_server_certificate_request(expiration_days)

if __name__ == "__main__":
    
    print("[INFO]: TLS certificate generation started")
    
    parser = argparse.ArgumentParser(description="TLS certificate generator")
    parser.add_argument("--output_path", help="Path to store certificates", required=True)
    parser.add_argument("--ip", help="Specify server IP address", required=True)
    parser.add_argument("--expiration_days", help="Specify certificate expiration in days", required=True, type=int)
    parser.add_argument("--ca_cer_path", help="Specify CA certificate path", default=None)
    parser.add_argument("--ca_key_path", help="Specify CA key path", default=None)
    args = parser.parse_args()

    Path(args.output_path).mkdir(parents=True, exist_ok=True)

    ca_cer_key_args_not_set = args.ca_cer_path is None or args.ca_key_path is None
    if ca_cer_key_args_not_set:
        args.ca_cer_path = f"{args.output_path}/ca.cer"
        print(f"[INFO]: arg CA_CER_PATH, defaulting to {args.ca_cer_path}")
        args.ca_key_path = f"{args.output_path}/ca.key"
        print(f"[INFO]: arg CA_KEY_PATH, defaulting to {args.ca_key_path}")

    if args.ip == "auto":
        args.ip = requests.get('https://api.ipify.org').text
    
    tls_cer_generator = tls_certificate_generator(
            Path(args.output_path), 
            Path(args.ca_cer_path),
            Path(args.ca_key_path),
            args.ip)
    
    ca_cer_key_pair_dont_exist = os.path.exists(args.ca_cer_path) == False or os.path.exists(args.ca_key_path) == False
    if ca_cer_key_args_not_set and ca_cer_key_pair_dont_exist:
        tls_cer_generator.generate_ca_certificate()
    else:
        print(f"[INFO]: CA certificate not generated, reason: it already exists in {args.output_path} or args --ca_cer_path and --ca_key_path are set")
    
    tls_cer_generator.generate_server_certificate(args.expiration_days)
    print("[INFO]: TLS certificate generation completed")