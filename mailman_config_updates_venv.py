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
        parser.add_argument('--listname', required=True, help='[obrigatorio] Nome da lista. Deve-se passar o nome da lista juntamente com o domínio (Ex.: test@domain.com.br).')
        parser.add_argument('--get', metavar='PROPERTY', required=False, help='[opcional] Informe o nome da propriedade da lista que você quer consultar. Se omitido, o script executa a ação padrão que é alterar as opções: advertised, anonymous_list, dmarc_mitigate_action e archive_policy.')
        parser.add_argument('--set', metavar='PROPERTY', required=False, help='[opcional] Configura uma propriedade na lista. Se omitido, o script executa a ação padrão que é alterar as opções: advertised, anonymous_list, dmarc_mitigate_action e archive_policy.')
        parser.add_argument('--value', metavar='PROPERTY VALUE', required=False, help='[opcional] Informe o valor da propriedade da lista. Deve ser usado com --set.')
        
        args = parser.parse_args()
        self.listname = args.listname

        self.validate_arguments(parser, args)

    def validate_arguments(self, parser, args):
        if self.listname and '@' not in self.listname:
            print(f"A lista '{self.listname}' foi passada sem um domínio.\n")
            parser.print_help()
            parser.exit(20)

        if bool(args.set) != bool(args.value):
            print("--set e --value devem ser usados juntos.\n")
            parser.print_help()
            parser.exit(21)

        self.execute_actions(args)

    def execute_actions(self, args):
        self.UrlAPI = f"http://localhost:8001/3.1/lists/{self.listname}/config"
        self.get_credentials()

        if args.get:
            self.do_get_request(args.get)
        elif args.set:
            self.do_set_request(args.set, args.value)
        else:
            self.build_patch()
            self.check_configuration_updates()

    def get_credentials(self):
        try:
            run_docker = subprocess.run(
                ["mailman", "info"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
                text=True
            )
            for line in run_docker.stdout.splitlines():
                if "REST credentials:" in line:
                    credentials = line.split("REST credentials:")[1].strip()
                    self.user, self.password = credentials.split(":", 1)
                    print(self.user, self.password)

        except subprocess.CalledProcessError as e:
            print("Erro ao executar o comando:", e)
            sys.exit(20)

    def build_patch(self):

        self.config_updates = {
            "advertised": False,
            "anonymous_list": False,
            "dmarc_mitigate_action": "munge_from",
            "archive_policy": "private"
        }

        for key in self.config_updates.keys():
            urlapi = self.UrlAPI + '/' + key
            self.do_patch_request(urlapi, key, self.config_updates[key])

    def verify_error_connection(self, consulta):

        try:
            consulta.raise_for_status()

        except HTTPError as http_err:
            print('\nHTTP error occurred. Are the parameters or values in the list correct?\n')
            sys.exit(12)

        except Exception as err:
            print('\nOther error occurred\n')
            sys.exit(12)

    def do_patch_request(self, UrlAPI, config, value):
        update_payload = {config: value}
        patch_request = requests.patch(UrlAPI, json=update_payload, auth=(self.user, self.password))
        self.verify_error_connection(patch_request)

    def do_get_request(self, list_property):
        build_get_request = self.UrlAPI + '/' + list_property
        get_request_result = requests.get(build_get_request, auth=(self.user, self.password))
        self.verify_error_connection(get_request_result)

        return_get_mode_dict = json.loads(get_request_result.content.decode('utf-8'))

        print(list_property + ' =', return_get_mode_dict[list_property])

    def do_set_request(self, list_property, property_value):
        build_set_request = self.UrlAPI + '/' + list_property
        set_payload = {list_property: property_value}

        set_request_result = requests.patch(build_set_request, json=set_payload, auth=(self.user, self.password))
        self.verify_error_connection(set_request_result)

        print(f"Configurando a propriedade '{list_property}' para ser igual a '{property_value}' na lista {self.listname}")
        self.do_get_request(list_property)

    def check_configuration_updates(self):
        get_request = requests.get(self.UrlAPI, auth=(self.user, self.password))
        self.verify_error_connection(get_request)

        return_get_mode_dict = json.loads(get_request.content.decode('utf-8'))

        for key in self.config_updates.keys():
            if return_get_mode_dict[key] != self.config_updates[key]: 
                print(f'O valor da propriedade {key} configurado no servidor é diferente do valor que deveria ser configurado.')

if __name__ == "__main__":

        init_class = Mailman()
