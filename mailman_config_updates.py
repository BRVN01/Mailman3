#!/usr/bin/env python3

from requests.exceptions import HTTPError
import requests
import json
import sys
import argparse
import subprocess

class Mailman:
          
    def __init__(self): 

        parser = argparse.ArgumentParser()
        parser.add_argument('--listname', required=True, help='Nome da lista. Deve-se passar o nome da lista juntamente com o domínio')

        args = parser.parse_args()

        self.listname = args.listname

        if self.listname:
            if '@' not in self.listname:
                raise argparse.ArgumentTypeError(f"A lista '{self.listname}' foi passada sem um domínio.")

        self.get_credentials()
        self.build()
        self.patch_api()
        self.get()

    def get_credentials(self):
        try:
            run_docker = subprocess.run(
                ["docker", "exec", "-i", "mailman-core", "mailman", "--run-as-root", "info"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
                text=True
            )
            for line in run_docker.stdout.splitlines():
                if "REST credentials:" in line:
                    credentials = line.split("REST credentials:")[1].strip()
                    self.user, self.password = credentials.split(":", 1)

        except subprocess.CalledProcessError as e:
            print("Erro ao executar o comando:", e)
            sys.exit(20)

    def build(self):

        self.UrlAPI = "http://localhost:8001/3.1/lists/" + self.listname + "/config"

        self.config_updates = {
            "advertised": False,
            "anonymous_list": False,
            "dmarc_mitigate_action": "munge_from",
            "archive_policy": "private"
        }

    def patch_api(self):
        
        for key in self.config_updates.keys():
            urlapi = self.UrlAPI + '/' + key
            self.patch(urlapi, key, self.config_updates[key])

    def verify_error_connection(self, consulta):

        try:
            consulta.raise_for_status()

        except HTTPError as http_err:
            print('\nHTTP error occurred.\n')
            sys.exit(12)

        except Exception as err:
            print('\nOther error occurred\n')
            sys.exit(12)

    def patch(self, UrlAPI, config, value):
        update_payload = {config: value}
        patch_api = requests.patch(UrlAPI, json=update_payload, auth=(self.user, self.password))
        self.verify_error_connection(patch_api)

    def get(self):
        get_api = requests.get(self.UrlAPI, auth=(self.user, self.password))
        self.verify_error_connection(get_api)

        return_get_mode_dict = json.loads(get_api.content.decode('utf-8'))

        for key in self.config_updates.keys():
            if return_get_mode_dict[key] != self.config_updates[key]: 
                print(f'O valor da propriedade {key} configurado no servidor é diferente do valor que deveria ser configurado.')

if __name__ == "__main__":

        init_class = Mailman()
