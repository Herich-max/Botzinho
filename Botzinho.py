import requests
import sys
import json
import uuid
import time
import os
import concurrent.futures
from colorama import init, Fore, Style
import argparse
import logging
from typing import Dict, List, Any, Optional

# Inicializa o colorama para suporte a cores no terminal
init(autoreset=True)

# Configura o logging para saídas mais profissionais com timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Endpoint da API
BASE_URL: str = "https://zefame-free.com/api_free.php"

# Headers para simular um navegador web
HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://zefame.com/",
    "Origin": "https://zefame.com"
}

# Mapeamento de nomes de serviços para maior clareza
SERVICE_NAMES: Dict[int, str] = {
    229: "TikTok Views",
    228: "TikTok Followers",
    232: "TikTok Free Likes",
    235: "TikTok Free Shares",
    236: "TikTok Free Favorites"
}

def clear_screen() -> None:
    """Limpa a tela do console de forma independente da plataforma."""
    os.system('cls' if os.name == 'nt' else 'clear')

def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Carrega a configuração de um arquivo JSON ou diretamente da API.
    
    :param config_file: Caminho opcional para o arquivo de configuração.
    :return: Dicionário com os dados de configuração.
    :raises SystemExit: Se houver erro no carregamento.
    """
    if config_file:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar configuração do arquivo: {e}")
            sys.exit(1)
    else:
        try:
            response = requests.get(f"{BASE_URL}?action=config", headers=HEADERS, timeout=15)
            response.raise_for_status()
            data = response.json()
            if not data.get("success"):
                raise ValueError(data.get("message", "Erro na API"))
            return data
        except Exception as e:
            logger.error(f"Erro ao carregar configuração da API: {e}")
            sys.exit(1)

def list_available_services(services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Lista os serviços disponíveis do TikTok e retorna os ativos.
    
    :param services: Lista de serviços da configuração.
    :return: Lista de serviços disponíveis.
    :raises SystemExit: Se não houver serviços disponíveis.
    """
    available_services = [s for s in services if s.get('available')]
    if not available_services:
        logger.warning("Nenhum serviço disponível no momento.")
        sys.exit(0)
    
    logger.info(f"{Fore.CYAN}Serviços disponíveis no TikTok:{Style.RESET_ALL}")
    for i, service in enumerate(available_services, 1):
        sid = service.get('id')
        name = SERVICE_NAMES.get(sid, service.get('name', '').strip() or "Desconhecido")
        rate = service.get('description', '').strip()
        rate_str = f"[{rate}]" if rate else ""
        timer = service.get('timer', '')
        status = f"{Fore.GREEN}[ATIVO]{Style.RESET_ALL}"
        logger.info(f"{i}. {name} — {status} {Fore.CYAN}{rate_str} {timer}{Style.RESET_ALL}")
    
    return available_services

def extract_video_id(video_url: str) -> str:
    """
    Extrai o ID do vídeo a partir da URL do TikTok.
    
    :param video_url: URL do vídeo.
    :return: ID do vídeo extraído.
    :raises SystemExit: Se houver falha na extração.
    """
    try:
        check_resp = requests.post(BASE_URL, data={"action": "checkVideoId", "link": video_url}, headers=HEADERS, timeout=15)
        check_resp.raise_for_status()
        video_id = check_resp.json().get("data", {}).get("videoId")
        if not video_id:
            raise ValueError("Não foi possível extrair o videoId")
        logger.info(f"{Fore.GREEN}Video ID extraído: {video_id}{Style.RESET_ALL}")
        return video_id
    except Exception as e:
        logger.error(f"Falha ao extrair video ID: {e}")
        sys.exit(1)

def run_service(
    service: Dict[str, Any],
    profile_url: str,
    video_url: str,
    video_id: str
) -> None:
    """
    Executa um serviço em loop infinito, enviando ordens para a API.
    
    :param service: Dicionário com dados do serviço.
    :param profile_url: URL do perfil TikTok.
    :param video_url: URL do vídeo TikTok.
    :param video_id: ID do vídeo extraído.
    """
    service_id = service.get('id')
    service_name = SERVICE_NAMES.get(service_id, service.get('name', '').strip() or "Desconhecido")
    timer_seconds = service.get('timerSeconds', 600)  # Padrão: 10 minutos

    logger.info(f"{Fore.MAGENTA}[INICIANDO]{Style.RESET_ALL} {service_name}")

    while True:
        try:
            # Seleciona o link apropriado com base no serviço
            link_to_use = profile_url if service_id == 228 else video_url  # 228: Followers
            video_id_to_use = "" if service_id == 228 else video_id

            # Prepara e envia a requisição de ordem
            order_data = {
                "service": service_id,
                "link": link_to_use,
                "uuid": str(uuid.uuid4()),
                "videoId": video_id_to_use
            }
            order_resp = requests.post(f"{BASE_URL}?action=order", data=order_data, headers=HEADERS, timeout=15)
            order_resp.raise_for_status()
            result = order_resp.json()

            if result.get("success"):
                msg = result.get('message', 'Enviado com sucesso!')
                logger.info(f"{Fore.GREEN}[SUCESSO]{Style.RESET_ALL} {service_name}: {msg}")
            else:
                msg = result.get('message', 'Erro desconhecido')
                logger.warning(f"{Fore.YELLOW}[AVISO]{Style.RESET_ALL} {service_name}: {msg}")

            # Aguarda o tempo definido pelo timer do serviço
            logger.info(f"{Fore.CYAN}[AGUARDANDO]{Style.RESET_ALL} {service_name}: {timer_seconds} segundos")
            time.sleep(timer_seconds)

        except requests.exceptions.RequestException as e:
            logger.error(f"{Fore.RED}[ERRO DE REDE]{Style.RESET_ALL} {service_name}: {e}")
            time.sleep(15)
        except json.JSONDecodeError:
            logger.error(f"{Fore.RED}[ERRO DE JSON]{Style.RESET_ALL} {service_name}: Resposta inválida")
            time.sleep(15)
        except Exception as e:
            logger.error(f"{Fore.RED}[ERRO GERAL]{Style.RESET_ALL} {service_name}: {e}")
            time.sleep(15)

def main() -> None:
    """Função principal que orquestra a execução do script."""
    clear_screen()

    # Parser de argumentos de linha de comando
    parser = argparse.ArgumentParser(
        description="Script profissional para boost de serviços TikTok via API.",
        epilog="Exemplo: python script.py --config config.json"
    )
    parser.add_argument('--config', type=str, help="Caminho para o arquivo de configuração JSON (opcional).")
    args = parser.parse_args()

    # Carrega a configuração
    data = load_config(args.config)
    services = data.get('data', {}).get('tiktok', {}).get('services', [])

    # Lista serviços disponíveis
    available_services = list_available_services(services)

    logger.info(f"\n{Fore.YELLOW}Iniciando todos os serviços disponíveis de forma concorrente...{Style.RESET_ALL}")

    # Obtém entradas do usuário com validação
    profile_url = input('Digite a URL do perfil TikTok: ').strip()
    video_url = input('Digite a URL do vídeo TikTok: ').strip()

    if not profile_url or not video_url:
        logger.error(f"{Fore.RED}Ambas as URLs são obrigatórias!{Style.RESET_ALL}")
        sys.exit(1)

    # Extrai o ID do vídeo
    video_id = extract_video_id(video_url)

    logger.info(f"{Fore.CYAN}Executando serviços em paralelo infinitamente...{Style.RESET_ALL}")
    logger.info(f"{Fore.YELLOW}Pressione Ctrl+C para interromper.{Style.RESET_ALL}\n")

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(available_services)) as executor:
            futures = [
                executor.submit(run_service, service, profile_url, video_url, video_id)
                for service in available_services
            ]
            concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)
    except KeyboardInterrupt:
        logger.warning(f"\n{Fore.YELLOW}Execução interrompida pelo usuário...{Style.RESET_ALL}")
    finally:
        logger.info(f"\n{Fore.GREEN}Programa encerrado com sucesso.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
