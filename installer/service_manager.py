import subprocess
import shutil
import json
import requests
import os
import sys
import platform
import re
from pathlib import Path

class ServiceManager:
    def __init__(self, project_root):
        self.project_root = project_root
        self.required_docker_version = "20.10.0"
        self.required_compose_version = "2.0.0"

    def check_system_requirements(self):
        print("Checking system requirements...")
        
        system = platform.system()
        if system not in ["Linux"]:
            print(f"Error: Unsupported operating system: {system}")
            sys.exit(1)

        self.check_docker_version()
        self.check_docker_compose_version()
        self.check_curl_installed()

        print("System requirements check passed!")

    def check_docker_version(self):
        try:
            result = subprocess.run(["docker", "--version"], check=True, capture_output=True, text=True)
            version_string = result.stdout.strip()
            if not self._version_check(version_string, self.required_docker_version):
                print(f"Error: Docker version {self.required_docker_version} or higher is required")
                print(f"Current version: {version_string}")
                sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"Error: Docker is not installed or not working properly")
            print(e.stderr.decode())
            sys.exit(1)
            
    def check_docker_compose_version(self):
        try:
            result = subprocess.run(["docker-compose", "--version"], check=True, capture_output=True, text=True)
            version_string = result.stdout.strip()
            if not self._version_check(version_string, self.required_compose_version):
                print(f"Error: Docker Compose version {self.required_compose_version} or higher is required")
                print(f"Current version: {version_string}")
                sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"Error: Docker Compose is not installed or not working properly")
            print(e.stderr.decode())
            sys.exit(1)
            
    def check_curl_installed(self):
        if not shutil.which("curl"):
            print("Error: Curl is not installed")
            sys.exit(1)

    def _version_check(self, version_string, required_version):
        version = re.search(r'\d+\.\d+\.\d+', version_string)
        if not version:
            return False
        return tuple(map(int, version.group().split('.'))) >= tuple(map(int, required_version.split('.')))

    def start_services(self, env):
        print("\nStarting services...")
        try:
            try:
                subprocess.run(["docker", "info"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                print("Error: Docker daemon is not running. Please start the Docker service and try again.")
                sys.exit(1)

            os.environ["DOCKER_HOST"] = "tcp://localhost:2376"
            os.environ["DOCKER_TLS_VERIFY"] = "1"
            os.environ["DOCKER_CERT_PATH"] = "/etc/nixopus/docker-certs"
            os.environ["DOCKER_CONTEXT"] = "nixopus" if env == "production" else "nixopus-staging"
            compose_cmd = ["docker", "compose"] if shutil.which("docker") else ["docker-compose"]
            if env == "staging":
                compose_cmd += ["-f", "../docker-compose-staging.yml"]
                print("Building and starting staging services...")
                result = subprocess.run(
                    compose_cmd + ["up", "--build", "-d"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                if result.returncode != 0:
                    print("Error building and starting services:")
                    print(result.stderr)
                    raise Exception("Failed to build and start services")
            else:
                compose_cmd += ["-f", "../docker-compose.yml"]
                print("Pulling production images...")
                pull_result = subprocess.run(
                    compose_cmd + ["pull"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                if pull_result.returncode != 0:
                    print("Error pulling images:")
                    print(pull_result.stderr)
                    raise Exception("Failed to pull images")
                
                print("Starting services...")
                result = subprocess.run(
                    compose_cmd + ["up", "-d"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                if result.returncode != 0:
                    print("Error starting services:")
                    print(result.stderr)
                    raise Exception("Failed to start services")
        except Exception as e:
            print(f"Error starting services: {str(e)}")
            sys.exit(1)
            
    def production_containers(self):
        return {
            "nixopus-api-container": "API service",
            "nixopus-db-container": "Database service",
            "nixopus-view-container": "View service",
            "nixopus-caddy-container": "Caddy service"
            # we will not check for redis service here because it is not strictly required for the api to run
        }
    
    def staging_containers(self):
        return {
            "nixopus-staging-api": "API service",
            "nixopus-staging-db": "Database service",
            "nixopus-staging-view": "View service",
        }

    def verify_installation(self,env):
        print("\nVerifying installation...")
        try:
            result = subprocess.run(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], capture_output=True, text=True)
            if result.returncode != 0:
                print("Error verifying installation:")
                print(result.stderr)
                sys.exit(1)
                
            running_containers = result.stdout.splitlines()
            required_containers = self.production_containers() if env == "production" else self.staging_containers()
            
            missing_containers = []
            for container, service_name in required_containers.items():
                container_running = any(
                    line.startswith(container) and "Up" in line
                    for line in running_containers
                )
                if not container_running:
                    missing_containers.append(service_name)

            if missing_containers:
                print("Error: The following services are not running:")
                for service in missing_containers:
                    print(f"  - {service}")
                sys.exit(1)

            print("All services are running successfully!")
        except Exception as e:
            print(f"Error verifying installation: {str(e)}")
            sys.exit(1)
    
    def setup_caddy(self, domains, env):
        print("\nSetting up Proxy...")
        try:
            current_config = None
            try:
                response = requests.get('http://localhost:2019/config')
                if response.status_code == 200:
                    current_config = response.json()
            except requests.exceptions.RequestException:
                current_config = None

            with open('../helpers/caddy.json', 'r') as f:
                config_str = f.read()
                config_str = config_str.replace('{env.APP_DOMAIN}', domains['app_domain'])
                config_str = config_str.replace('{env.API_DOMAIN}', domains['api_domain'])
                app_reverse_proxy_url = "nixopus-view:7443" if env == "production" else "nixopus-staging-view:7444"
                api_reverse_proxy_url = "nixopus-api:8443" if env == "production" else "nixopus-staging-api:8444"
                config_str = config_str.replace('{env.APP_REVERSE_PROXY_URL}', app_reverse_proxy_url)
                config_str = config_str.replace('{env.API_REVERSE_PROXY_URL}', api_reverse_proxy_url)
                new_config = json.loads(config_str)

            if current_config and 'apps' in current_config and 'http' in current_config['apps'] and 'servers' in current_config['apps']['http'] and 'nixopus' in current_config['apps']['http']['servers']:
                new_routes = new_config['apps']['http']['servers']['nixopus'].get('routes', [])
                if new_routes:
                    for route in new_routes:
                        response = requests.post(
                            'http://localhost:2019/config/apps/http/servers/nixopus/routes/...',
                            json=[route],
                            headers={'Content-Type': 'application/json'}
                        )
                        if response.status_code != 200:
                            print(f"Failed to append route: {response.text}")
                            raise Exception("Failed to append route to Caddy configuration")
            else:
                response = requests.post(
                    'http://localhost:2019/load',
                    json=new_config,
                    headers={'Content-Type': 'application/json'}
                )
                if response.status_code != 200:
                    print("Failed to load Caddy configuration:")
                    print(response.text)
                    raise Exception("Failed to load Caddy configuration")

            print("Caddy configuration loaded successfully")
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Caddy: {str(e)}")
        except Exception as e:
            print(f"Error setting up Caddy: {str(e)}")
    
    def check_api_up_status(self, port):
        print(f"Checking API status on port {port}...")
        try:
            response = requests.get(f"http://localhost:{port}/api/v1/health",verify=False)
            if response.status_code == 200:
                return True
            return False
        except requests.exceptions.RequestException as e:
            print(f"Error checking API status: {str(e)}")
            return False
    
    def setup_admin(self, email, password, port):
        print("\nSetting up admin...")
        username = email.split('@')[0]
        
        try:
            response = requests.post(
                f"http://localhost:{port}/api/v1/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "type": "admin",
                    "username": username,
                    "organization": ""
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print("Admin setup completed successfully")
                return
                
            if response.status_code == 400 and "admin already registered" in response.text:
                print("Admin already registered")
                return
                
            error_msg = response.json().get("message", "Unknown error")
            print(f"API Error: {error_msg}")
            raise Exception(f"API Error: {error_msg}")
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            raise Exception(f"Failed to connect to API: {str(e)}")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON response: {response.text}")
            raise Exception(f"Invalid response from API: {str(e)}")
